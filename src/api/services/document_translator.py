"""Document translation service.

Translates a document segment by segment and writes the results back into the
original file, so the download is the uploaded document with translated text
rather than a plain-text transcript of it.
"""

import asyncio
from datetime import UTC, datetime

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.models.document_artifact import DocumentArtifact
from src.api.models.document_job import DocumentJob
from src.api.models.document_result import DocumentResult
from src.api.models.user import User
from src.api.services.document_format import (
    MAX_SEGMENT_CHARS,
    DocumentFormatError,
    FormatHandler,
    Segment,
    get_handler,
)
from src.api.services.provider_manager import ProviderManager
from src.api.services.providers.base import TranslationProvider
from src.api.services.text_chunker import TextChunker

log = structlog.get_logger()

# Segments are independent, so several can be in flight at once. Kept low enough
# to stay well inside third-party rate limits and not to swamp the model worker.
MAX_CONCURRENT_SEGMENTS = 4
# One retry covers the transient failures (a rate limit, a dropped connection)
# that make up most segment errors.
SEGMENT_ATTEMPTS = 2


class DocumentTranslator:
    """Extracts a document's text, translates it, and rebuilds the same file type."""

    def __init__(self, provider_manager: ProviderManager, chunker: TextChunker | None = None):
        self.provider_manager = provider_manager
        self.chunker = chunker or TextChunker()

    async def translate_document(
        self,
        job: DocumentJob,
        file_bytes: bytes,
        user: User,
        db: AsyncSession,
        provider_key_id: str | None = None,
    ) -> None:
        """Translate an uploaded document and update its job record.

        Runs as a background task. Credits are reserved before any translation
        happens, and billing counts each distinct string once, so a spreadsheet
        that repeats a label two hundred times is charged for it once.
        """
        try:
            job.status = "processing"
            await db.commit()

            handler = get_handler(job.original_filename, target_lang=job.target_lang)
            segments = handler.extract(file_bytes)
            pending = [segment for segment in segments if segment.translatable]

            log.info(
                "document_translation_started",
                job_id=str(job.id),
                provider=job.provider,
                source_lang=job.source_lang,
                target_lang=job.target_lang,
                segments=len(segments),
                translatable=len(pending),
            )

            resolved = await self.provider_manager.resolve(
                provider_name=job.provider,
                user=user,
                db=db,
                provider_key_id=provider_key_id,
            )

            unique_texts = sorted({segment.text for segment in pending})
            billable_chars = sum(len(text) for text in unique_texts)

            if not resolved.used_own_key and job.provider != "marianmt":
                allowed = await self.provider_manager.deduct_credits(
                    user=user,
                    db=db,
                    provider_name=job.provider,
                    char_count=billable_chars,
                )
                if not allowed:
                    log.warning(
                        "insufficient_credits_for_document",
                        job_id=str(job.id),
                        user_id=str(user.id),
                        billable_chars=billable_chars,
                    )
                    await self._fail(job, db, "Insufficient credits for document translation")
                    return

            translated_by_text, failures = await self._translate_texts(
                texts=unique_texts,
                provider=resolved.provider,
                source_lang=job.source_lang,
                target_lang=job.target_lang,
                job_id=str(job.id),
            )

            if failures and not translated_by_text:
                await self._fail(
                    job, db, f"Translation failed for all {len(failures)} text segments"
                )
                return

            translations = {
                segment.id: translated_by_text[segment.text]
                for segment in pending
                if segment.text in translated_by_text
            }
            output_bytes = handler.rebuild(file_bytes, translations)

            self._store(
                job=job,
                db=db,
                handler=handler,
                segments=segments,
                translations=translations,
                output_bytes=output_bytes,
                billable_chars=billable_chars,
                failed_count=len(pending) - len(translations),
            )

            job.status = "completed"
            job.completed_at = datetime.now(UTC)
            if failures:
                # Surfaced rather than swallowed: the file is usable, but the user
                # needs to know some of it is still in the source language.
                job.error_message = (
                    f"{len(failures)} of {len(unique_texts)} text segments could not be "
                    "translated and kept their original wording."
                )
            await db.commit()

            log.info(
                "document_translation_completed",
                job_id=str(job.id),
                segments=len(segments),
                translated=len(translations),
                failed=len(failures),
                billable_chars=billable_chars,
                output_bytes=len(output_bytes),
                format_preserved=handler.preserves_format,
            )

        except DocumentFormatError as exc:
            log.warning("document_format_error", job_id=str(job.id), error=str(exc))
            await self._fail(job, db, str(exc))
        except Exception as exc:
            log.error("document_translation_failed", job_id=str(job.id), error=str(exc))
            await self._fail(job, db, str(exc))

    async def _translate_texts(
        self,
        texts: list[str],
        provider: TranslationProvider,
        source_lang: str,
        target_lang: str,
        job_id: str,
    ) -> tuple[dict[str, str], list[str]]:
        """Translate each distinct string, returning successes and failures.

        A segment that keeps failing is left out of the result so it falls back to
        its source text. Writing an error marker into the document instead would
        corrupt the very formatting this pipeline exists to protect.
        """
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_SEGMENTS)
        translated: dict[str, str] = {}
        failures: list[str] = []

        async def run(text: str) -> None:
            async with semaphore:
                for attempt in range(1, SEGMENT_ATTEMPTS + 1):
                    try:
                        translated[text] = await self._translate_one(
                            text, provider, source_lang, target_lang
                        )
                        return
                    except Exception as exc:
                        if attempt == SEGMENT_ATTEMPTS:
                            failures.append(text)
                            log.warning(
                                "segment_translation_failed",
                                job_id=job_id,
                                chars=len(text),
                                error=str(exc),
                            )
                        else:
                            await asyncio.sleep(0.5 * attempt)

        await asyncio.gather(*(run(text) for text in texts))
        return translated, failures

    async def _translate_one(
        self,
        text: str,
        provider: TranslationProvider,
        source_lang: str,
        target_lang: str,
    ) -> str:
        """Translate one segment, splitting it up only if it exceeds provider limits."""
        if len(text) <= MAX_SEGMENT_CHARS:
            return await provider.translate(
                text=text, source_lang=source_lang, target_lang=target_lang
            )

        chunks = self.chunker.chunk_text(text, max_chunk_size=MAX_SEGMENT_CHARS)
        parts = [
            await provider.translate(text=chunk, source_lang=source_lang, target_lang=target_lang)
            for chunk in chunks
        ]
        return " ".join(parts)

    def _store(
        self,
        job: DocumentJob,
        db: AsyncSession,
        handler: FormatHandler,
        segments: list[Segment],
        translations: dict[int, str],
        output_bytes: bytes,
        billable_chars: int,
        failed_count: int,
    ) -> None:
        """Persist the rebuilt file plus a plain-text rendering for previews."""
        preview = "\n".join(
            translations.get(segment.id, segment.text)
            for segment in segments
            if segment.text.strip()
        )

        db.add(
            DocumentResult(
                job_id=job.id,
                translated_content=preview,
                chunk_count=len(segments),
                total_characters=billable_chars,
            )
        )
        db.add(
            DocumentArtifact(
                job_id=job.id,
                content=output_bytes,
                filename=handler.output_filename(job.original_filename),
                mime_type=handler.output_mime,
                byte_size=len(output_bytes),
                format_preserved=handler.preserves_format,
                segment_count=len(segments),
                translated_segments=len(translations),
                failed_segments=failed_count,
            )
        )

    async def _fail(self, job: DocumentJob, db: AsyncSession, message: str) -> None:
        job.status = "failed"
        job.error_message = message
        job.completed_at = datetime.now(UTC)
        await db.commit()
