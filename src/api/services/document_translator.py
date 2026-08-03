"""Document translation service.

Translates parsed document paragraphs using the ProviderManager,
tracks progress, and stores results in the database.
"""

import asyncio
from datetime import UTC, datetime

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.models.document_job import DocumentJob
from src.api.models.document_result import DocumentResult
from src.api.models.user import User
from src.api.services.document_parser import MAX_CHUNK_SIZE, DocumentParser
from src.api.services.provider_manager import ProviderManager
from src.api.services.providers.base import TranslationProvider

log = structlog.get_logger()

# Bounds how many paragraphs are in flight to a provider at once. Translating
# per-paragraph (rather than in a few large joined chunks) is what lets us
# rebuild a translated DOCX/PDF with the original paragraph structure intact.
MAX_CONCURRENT_TRANSLATIONS = 5


class DocumentTranslator:
    """Orchestrates document translation, one paragraph at a time.

    Translates each paragraph via the resolved provider (with bounded
    concurrency), reassembles the flat text output, rebuilds a
    format-preserving DOCX/PDF when possible, and persists the result.
    """

    def __init__(self, provider_manager: ProviderManager, parser: DocumentParser):
        self.provider_manager = provider_manager
        self.parser = parser

    async def translate_document(
        self,
        job: DocumentJob,
        paragraphs: list[str],
        original_file_bytes: bytes,
        user: User,
        db: AsyncSession,
        provider_key_id: str | None = None,
    ) -> None:
        """Translate a full document and update job status.

        This is designed to run as a background task. It:
        1. Updates job status to processing
        2. Reserves credits based on estimated character count (if using admin key)
        3. Translates each paragraph (bounded concurrency)
        4. Reassembles the output and rebuilds the original format when possible
        5. Updates job status to completed (or failed)

        Args:
            job: The DocumentJob record to process.
            paragraphs: Non-empty paragraph/page texts extracted from the
                original document, in order.
            original_file_bytes: The originally uploaded file's raw bytes,
                needed to rebuild a translated DOCX preserving formatting.
            user: The user who submitted the job.
            db: Database session.
            provider_key_id: Optional BYOK key ID.
        """
        try:
            # Mark as processing
            job.status = "processing"
            await db.commit()

            log.info(
                "document_translation_started",
                job_id=str(job.id),
                provider=job.provider,
                source_lang=job.source_lang,
                target_lang=job.target_lang,
            )

            # Resolve the provider first so we know whether this run uses the
            # user's own key (free) or the platform admin key (costs credits).
            resolved = await self.provider_manager.resolve(
                provider_name=job.provider,
                user=user,
                db=db,
                provider_key_id=provider_key_id,
            )
            provider = resolved.provider

            # Reserve credits BEFORE translation if using admin key
            total_chars = len("\n\n".join(paragraphs))
            if not resolved.used_own_key and job.provider != "marianmt":
                credit_ok = await self.provider_manager.deduct_credits(
                    user=user,
                    db=db,
                    provider_name=job.provider,
                    char_count=total_chars,
                )
                if not credit_ok:
                    log.warning(
                        "insufficient_credits_for_document",
                        job_id=str(job.id),
                        user_id=str(user.id),
                        estimated_chars=total_chars,
                    )
                    job.status = "failed"
                    job.error_message = "Insufficient credits for document translation"
                    job.completed_at = datetime.now(UTC)
                    await db.commit()
                    return

            # Translate paragraph-by-paragraph (bounded concurrency) so
            # paragraph boundaries survive for format-preserving rebuild.
            semaphore = asyncio.Semaphore(MAX_CONCURRENT_TRANSLATIONS)
            translated_paragraphs = await asyncio.gather(
                *(
                    self._translate_paragraph(provider, job, index, paragraph, semaphore)
                    for index, paragraph in enumerate(paragraphs)
                )
            )

            # Reassemble translated content (flat text, used for preview/.txt output)
            translated_content = "\n\n".join(translated_paragraphs)

            # Rebuild the original format when supported; fall back to plain
            # text (translated_file_bytes stays None) if rebuild fails.
            extension = self.parser.get_extension(job.original_filename)
            output_format = "txt"
            translated_file_bytes: bytes | None = None
            if extension == "docx":
                try:
                    translated_file_bytes = self.parser.build_translated_docx(
                        original_file_bytes, list(translated_paragraphs)
                    )
                    output_format = "docx"
                except Exception as rebuild_err:
                    log.warning("docx_rebuild_failed", job_id=str(job.id), error=str(rebuild_err))
            elif extension == "pdf":
                try:
                    translated_file_bytes = self.parser.build_translated_pdf(
                        list(translated_paragraphs)
                    )
                    output_format = "pdf"
                except Exception as rebuild_err:
                    log.warning("pdf_rebuild_failed", job_id=str(job.id), error=str(rebuild_err))

            # Store result
            result = DocumentResult(
                job_id=job.id,
                translated_content=translated_content,
                chunk_count=len(paragraphs),
                total_characters=total_chars,
                translated_file_bytes=translated_file_bytes,
                output_format=output_format,
            )
            db.add(result)

            # Update job status
            job.status = "completed"
            job.completed_at = datetime.now(UTC)
            await db.commit()

            log.info(
                "document_translation_completed",
                job_id=str(job.id),
                paragraphs=len(paragraphs),
                total_chars=total_chars,
                output_format=output_format,
            )

        except Exception as e:
            log.error(
                "document_translation_failed",
                job_id=str(job.id),
                error=str(e),
            )
            job.status = "failed"
            job.error_message = str(e)
            job.completed_at = datetime.now(UTC)
            await db.commit()

    async def _translate_paragraph(
        self,
        provider: TranslationProvider,
        job: DocumentJob,
        index: int,
        paragraph: str,
        semaphore: asyncio.Semaphore,
    ) -> str:
        """Translate a single paragraph, splitting it further if oversized.

        On failure, returns an inline error marker rather than raising, so one
        bad paragraph doesn't fail the whole document (matches prior chunk-level
        behavior).
        """
        async with semaphore:
            try:
                if len(paragraph) <= MAX_CHUNK_SIZE:
                    return await provider.translate(
                        text=paragraph,
                        source_lang=job.source_lang,
                        target_lang=job.target_lang,
                    )

                # Paragraph too large for one call: split, translate the
                # pieces, and rejoin so the caller still gets one string back
                # per input paragraph (preserving the 1:1 index mapping).
                sub_chunks = self.parser.chunk_text(paragraph)
                translated_parts = [
                    await provider.translate(
                        text=sub_chunk,
                        source_lang=job.source_lang,
                        target_lang=job.target_lang,
                    )
                    for sub_chunk in sub_chunks
                ]
                return " ".join(translated_parts)
            except Exception as err:
                log.error(
                    "paragraph_translation_failed",
                    job_id=str(job.id),
                    paragraph_index=index,
                    error=str(err),
                )
                return f"[Translation error in section {index + 1}: {err}]"
