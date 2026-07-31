"""Document translation service.

Translates parsed document chunks using the ProviderManager,
tracks progress, and stores results in the database.
"""

from datetime import datetime, timezone

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.models.document_job import DocumentJob
from src.api.models.document_result import DocumentResult
from src.api.models.user import User
from src.api.services.document_parser import DocumentParser
from src.api.services.provider_manager import ProviderManager

log = structlog.get_logger()


class DocumentTranslator:
    """Orchestrates document translation using chunked processing.

    Translates each chunk via the resolved provider, reassembles
    the output, and persists the result to the database.
    """

    def __init__(self, provider_manager: ProviderManager, parser: DocumentParser):
        self.provider_manager = provider_manager
        self.parser = parser

    async def translate_document(
        self,
        job: DocumentJob,
        text_content: str,
        user: User,
        db: AsyncSession,
        provider_key_id: str | None = None,
    ) -> None:
        """Translate a full document and update job status.

        This is designed to run as a background task. It:
        1. Updates job status to processing
        2. Reserves credits based on estimated character count (if using admin key)
        3. Chunks the text
        4. Translates each chunk
        5. Reassembles and stores the result
        6. Updates job status to completed (or failed)

        Args:
            job: The DocumentJob record to process.
            text_content: Extracted text from the document.
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

            # Reserve credits BEFORE translation if using admin key
            total_chars = len(text_content)
            if not provider_key_id and job.provider != "marianmt":
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
                    job.completed_at = datetime.now(timezone.utc)
                    await db.commit()
                    return

            # Get the translation provider
            provider = await self.provider_manager.get_provider(
                provider_name=job.provider,
                user=user,
                db=db,
                provider_key_id=provider_key_id,
            )

            # Chunk the text
            chunks = self.parser.chunk_text(text_content)
            translated_chunks: list[str] = []

            for i, chunk in enumerate(chunks):
                try:
                    translated = await provider.translate(
                        text=chunk,
                        source_lang=job.source_lang,
                        target_lang=job.target_lang,
                    )
                    translated_chunks.append(translated)

                    log.debug(
                        "chunk_translated",
                        job_id=str(job.id),
                        chunk_index=i,
                        chunk_chars=len(chunk),
                    )
                except Exception as chunk_err:
                    log.error(
                        "chunk_translation_failed",
                        job_id=str(job.id),
                        chunk_index=i,
                        error=str(chunk_err),
                    )
                    # If a chunk fails, include error marker but continue
                    translated_chunks.append(
                        f"[Translation error in section {i + 1}: {chunk_err}]"
                    )

            # Reassemble translated content
            translated_content = "\n\n".join(translated_chunks)

            # Store result
            result = DocumentResult(
                job_id=job.id,
                translated_content=translated_content,
                chunk_count=len(chunks),
                total_characters=total_chars,
            )
            db.add(result)

            # Update job status
            job.status = "completed"
            job.completed_at = datetime.now(timezone.utc)
            await db.commit()

            log.info(
                "document_translation_completed",
                job_id=str(job.id),
                chunks=len(chunks),
                total_chars=total_chars,
            )

        except Exception as e:
            log.error(
                "document_translation_failed",
                job_id=str(job.id),
                error=str(e),
            )
            job.status = "failed"
            job.error_message = str(e)
            job.completed_at = datetime.now(timezone.utc)
            await db.commit()
