"""Document translation router.

Provides endpoints for uploading documents, tracking translation jobs,
and downloading translated results.
"""

import asyncio
from urllib.parse import quote

import structlog
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlalchemy import delete as sql_delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.database import async_session, get_db
from src.api.middleware.dependencies import get_current_user
from src.api.models.document_job import DocumentJob
from src.api.models.document_result import DocumentResult
from src.api.models.user import User
from src.api.services.document_parser import (
    SUPPORTED_FORMATS,
    DocumentParseError,
    DocumentParser,
)
from src.api.services.document_translator import DocumentTranslator
from src.api.services.provider_manager import SUPPORTED_PROVIDERS, ProviderManager
from src.shared.config import APISettings

log = structlog.get_logger()
router = APIRouter(prefix="/documents", tags=["documents"])

# File size limit: 10 MB
MAX_FILE_SIZE = 10 * 1024 * 1024

# Track background tasks to prevent silent exception swallowing
_background_tasks: set[asyncio.Task] = set()


# Response models
class DocumentJobResponse(BaseModel):
    id: str
    original_filename: str
    file_size_bytes: int
    source_lang: str
    target_lang: str
    provider: str
    status: str
    error_message: str | None
    created_at: str
    completed_at: str | None


class DocumentJobListResponse(BaseModel):
    jobs: list[DocumentJobResponse]
    total: int


class DocumentJobDetailResponse(DocumentJobResponse):
    chunk_count: int | None = None
    total_characters: int | None = None
    translated_preview: str | None = None


class DocumentDownloadResponse(BaseModel):
    job_id: str
    original_filename: str
    translated_content: str
    chunk_count: int
    total_characters: int


def _job_to_response(job: DocumentJob) -> DocumentJobResponse:
    return DocumentJobResponse(
        id=str(job.id),
        original_filename=job.original_filename,
        file_size_bytes=job.file_size_bytes,
        source_lang=job.source_lang,
        target_lang=job.target_lang,
        provider=job.provider,
        status=job.status,
        error_message=job.error_message,
        created_at=job.created_at.isoformat(),
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
    )


@router.post("/translate", response_model=DocumentJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_and_translate(
    file: UploadFile = File(...),
    source_lang: str = Form(...),
    target_lang: str = Form(...),
    provider: str = Form(default="marianmt"),
    provider_key_id: str | None = Form(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentJobResponse:
    """Upload a document for translation.

    Accepts PDF, DOCX, or TXT files up to 10MB.
    Creates a background translation job and returns immediately.

    The job status can be polled via GET /api/v1/documents/jobs/{job_id}.
    """
    # Validate provider
    if provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported provider: {provider}. Supported: {', '.join(SUPPORTED_PROVIDERS)}",
        )

    # Validate file format
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must have a filename",
        )

    extension = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if extension not in SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format: .{extension}. "
            f"Supported formats: {', '.join(sorted(SUPPORTED_FORMATS))}",
        )

    # Read and validate file size
    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024 * 1024)}MB. "
            f"Your file is {len(file_bytes) / (1024 * 1024):.1f}MB.",
        )

    if len(file_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is empty.",
        )

    # Parse the document to extract text
    parser = DocumentParser()
    try:
        text_content = parser.parse(file_bytes, file.filename)
    except DocumentParseError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # Create the job record
    job = DocumentJob(
        user_id=user.id,
        original_filename=file.filename,
        file_size_bytes=len(file_bytes),
        source_lang=source_lang,
        target_lang=target_lang,
        provider=provider,
        status="pending",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    log.info(
        "document_job_created",
        job_id=str(job.id),
        user_id=str(user.id),
        filename=file.filename,
        size_bytes=len(file_bytes),
        provider=provider,
    )

    # Launch background translation task with proper exception tracking
    settings = APISettings()
    provider_manager = ProviderManager(settings)
    translator = DocumentTranslator(provider_manager, parser)

    task = asyncio.create_task(
        _run_translation_background(
            translator=translator,
            job_id=job.id,
            text_content=text_content,
            user_id=user.id,
            provider_key_id=provider_key_id,
        )
    )
    # Store task reference to prevent garbage collection and add exception logging
    _background_tasks.add(task)
    task.add_done_callback(_task_done_callback)

    return _job_to_response(job)


def _task_done_callback(task: asyncio.Task) -> None:
    """Log unhandled exceptions from background translation tasks."""
    _background_tasks.discard(task)
    if task.cancelled():
        log.warning("background_translation_task_cancelled", task_name=task.get_name())
        return
    exc = task.exception()
    if exc:
        log.error(
            "background_translation_task_failed",
            task_name=task.get_name(),
            error=str(exc),
            error_type=type(exc).__name__,
        )


async def _run_translation_background(
    translator: DocumentTranslator,
    job_id: object,
    text_content: str,
    user_id: object,
    provider_key_id: str | None,
) -> None:
    """Run document translation in a background task with its own DB session."""
    async with async_session() as db:
        # Re-fetch job and user in this session
        job = await db.get(DocumentJob, job_id)
        user = await db.get(User, user_id)

        if not job or not user:
            log.error("background_task_missing_records", job_id=str(job_id))
            return

        await translator.translate_document(
            job=job,
            text_content=text_content,
            user=user,
            db=db,
            provider_key_id=provider_key_id,
        )


@router.get("/jobs", response_model=DocumentJobListResponse)
async def list_jobs(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 20,
    offset: int = 0,
) -> DocumentJobListResponse:
    """List all document translation jobs for the current user."""
    # Get total count
    from sqlalchemy import func

    count_result = await db.execute(select(func.count()).where(DocumentJob.user_id == user.id))
    total = count_result.scalar() or 0

    # Get jobs
    result = await db.execute(
        select(DocumentJob)
        .where(DocumentJob.user_id == user.id)
        .order_by(DocumentJob.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    jobs = result.scalars().all()

    return DocumentJobListResponse(
        jobs=[_job_to_response(j) for j in jobs],
        total=total,
    )


@router.get("/jobs/{job_id}", response_model=DocumentJobDetailResponse)
async def get_job_status(
    job_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentJobDetailResponse:
    """Get detailed status of a document translation job."""
    result = await db.execute(
        select(DocumentJob).where(DocumentJob.id == job_id, DocumentJob.user_id == user.id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document job not found",
        )

    # Build detail response
    response = DocumentJobDetailResponse(
        id=str(job.id),
        original_filename=job.original_filename,
        file_size_bytes=job.file_size_bytes,
        source_lang=job.source_lang,
        target_lang=job.target_lang,
        provider=job.provider,
        status=job.status,
        error_message=job.error_message,
        created_at=job.created_at.isoformat(),
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
    )

    # Include result info if completed
    if job.result:
        response.chunk_count = job.result.chunk_count
        response.total_characters = job.result.total_characters
        # Preview: first 500 characters of translated content
        response.translated_preview = job.result.translated_content[:500]

    return response


@router.get("/jobs/{job_id}/download")
async def download_translated_document(
    job_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PlainTextResponse:
    """Download the translated document content as a text file.

    Only available for completed jobs. Returns the translated text
    with Content-Disposition header for file download.
    """
    result = await db.execute(
        select(DocumentJob).where(DocumentJob.id == job_id, DocumentJob.user_id == user.id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document job not found",
        )

    if job.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job is not completed yet. Current status: {job.status}",
        )

    if not job.result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Translation result not found",
        )

    # Generate a filename based on original
    original_name = (
        job.original_filename.rsplit(".", 1)[0]
        if "." in job.original_filename
        else job.original_filename
    )
    download_filename = f"{original_name}-translated.txt"

    # Content-Disposition headers must be latin-1 encodable, but filenames can
    # contain arbitrary Unicode (e.g. Vietnamese diacritics). Provide an ASCII
    # fallback plus the RFC 5987 filename* form so browsers use the real name.
    ascii_filename = download_filename.encode("ascii", "ignore").decode("ascii") or "download.txt"
    encoded_filename = quote(download_filename)

    return PlainTextResponse(
        content=job.result.translated_content,
        headers={
            "Content-Disposition": (
                f'attachment; filename="{ascii_filename}"; '
                f"filename*=UTF-8''{encoded_filename}"
            ),
        },
    )


VALID_JOB_STATUSES = ("pending", "processing", "completed", "failed")
FINISHED_JOB_STATUSES = ("completed", "failed")


class DeleteJobsResponse(BaseModel):
    deleted: int


@router.delete("/jobs", response_model=DeleteJobsResponse)
async def delete_jobs(
    job_status: str | None = Query(default=None, alias="status"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DeleteJobsResponse:
    """Bulk-delete the current user's document jobs.

    Without a ``status`` filter this clears every finished job (completed and
    failed) and leaves in-flight work alone. Pass ``status`` to target a single
    state, e.g. ``?status=completed``.
    """
    if job_status is None:
        target_statuses = list(FINISHED_JOB_STATUSES)
    elif job_status in VALID_JOB_STATUSES:
        target_statuses = [job_status]
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status: {job_status}. Valid values: {', '.join(VALID_JOB_STATUSES)}",
        )

    id_result = await db.execute(
        select(DocumentJob.id).where(
            DocumentJob.user_id == user.id,
            DocumentJob.status.in_(target_statuses),
        )
    )
    job_ids = list(id_result.scalars().all())
    if not job_ids:
        return DeleteJobsResponse(deleted=0)

    # Remove stored translations first, then the jobs themselves. Bulk deletes
    # bypass ORM cascades, so the child rows are handled explicitly.
    await db.execute(sql_delete(DocumentResult).where(DocumentResult.job_id.in_(job_ids)))
    await db.execute(sql_delete(DocumentJob).where(DocumentJob.id.in_(job_ids)))
    await db.commit()

    log.info(
        "document_jobs_bulk_deleted",
        user_id=str(user.id),
        count=len(job_ids),
        statuses=target_statuses,
    )
    return DeleteJobsResponse(deleted=len(job_ids))


@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a single document job and its stored translation."""
    result = await db.execute(
        select(DocumentJob).where(DocumentJob.id == job_id, DocumentJob.user_id == user.id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document job not found",
        )

    if job.status in ("pending", "processing"):
        # Allowed on purpose: a job wedged in an active state would otherwise be
        # impossible to clear. The background task tolerates a missing record.
        log.warning(
            "document_job_deleted_while_active",
            job_id=job_id,
            user_id=str(user.id),
            job_status=job.status,
        )

    await db.delete(job)
    await db.commit()
    log.info("document_job_deleted", job_id=job_id, user_id=str(user.id))
