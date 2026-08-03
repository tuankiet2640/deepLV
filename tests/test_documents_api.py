"""HTTP-level tests for the document endpoints.

Covers what a client actually observes: which uploads are rejected up front, and
that a completed job downloads as a real binary file with the right content type
and filename rather than as plain text.
"""

import io
import uuid

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.api.models import Base
from src.api.models.document_artifact import DocumentArtifact
from src.api.models.document_job import DocumentJob
from src.api.models.document_result import DocumentResult
from src.api.models.user import User
from tests.document_fixtures import build_docx

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


@pytest_asyncio.fixture
async def api():
    """A minimal app carrying only the documents router.

    Built here instead of importing ``src.api.main`` so the test exercises the
    document endpoints without dragging in the model worker, Redis or the
    language-detection model.
    """
    from fastapi import FastAPI

    from src.api.database import get_db
    from src.api.middleware.dependencies import get_current_user
    from src.api.routers import documents

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    user = User(
        id=uuid.uuid4(),
        email="doc-tester@example.com",
        password_hash="x",
        credits_balance=1000.0,
    )
    async with factory() as db:
        db.add(user)
        await db.commit()

    app = FastAPI()
    app.include_router(documents.router, prefix="/api/v1")

    async def override_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, factory, user

    await engine.dispose()


async def test_formats_endpoint_describes_every_supported_type(api):
    client, _, _ = api
    response = await client.get("/api/v1/documents/formats")
    assert response.status_code == 200

    body = response.json()
    by_extension = {item["extension"]: item for item in body["formats"]}
    assert set(by_extension) == {"docx", "pptx", "xlsx", "pdf", "html", "htm", "txt"}
    assert by_extension["docx"]["format_preserved"] is True
    # PDF is the one format whose output type differs from its input.
    assert by_extension["pdf"]["format_preserved"] is False
    assert by_extension["pdf"]["output_extension"] == ".docx"
    assert by_extension["pdf"]["note"]
    assert body["max_file_size_bytes"] == 10 * 1024 * 1024


async def test_unsupported_extension_is_rejected(api):
    client, _, _ = api
    response = await client.post(
        "/api/v1/documents/translate",
        files={"file": ("archive.zip", b"PK\x03\x04rubbish", "application/zip")},
        data={"source_lang": "en", "target_lang": "de", "provider": "marianmt"},
    )
    assert response.status_code == 400
    assert "Unsupported file format" in response.json()["detail"]


async def test_corrupt_document_is_rejected_before_a_job_is_created(api):
    client, factory, _ = api
    response = await client.post(
        "/api/v1/documents/translate",
        files={"file": ("broken.docx", b"not really a docx", DOCX_MIME)},
        data={"source_lang": "en", "target_lang": "de", "provider": "marianmt"},
    )
    assert response.status_code == 400
    assert "Could not read DOCX" in response.json()["detail"]

    # The upload failed synchronously, so the user has no phantom job to poll.
    async with factory() as db:
        from sqlalchemy import func, select

        count = await db.execute(select(func.count()).select_from(DocumentJob))
        assert count.scalar() == 0


async def test_document_without_translatable_text_is_rejected(api):
    client, _, _ = api
    response = await client.post(
        "/api/v1/documents/translate",
        files={"file": ("numbers.txt", b"42\n7\n1,000\n", "text/plain")},
        data={"source_lang": "en", "target_lang": "de", "provider": "marianmt"},
    )
    assert response.status_code == 400
    assert "No translatable text" in response.json()["detail"]


async def test_empty_file_is_rejected(api):
    client, _, _ = api
    response = await client.post(
        "/api/v1/documents/translate",
        files={"file": ("empty.txt", b"", "text/plain")},
        data={"source_lang": "en", "target_lang": "de", "provider": "marianmt"},
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


async def test_unknown_provider_is_rejected(api):
    client, _, _ = api
    response = await client.post(
        "/api/v1/documents/translate",
        files={"file": ("a.txt", b"Hello world\n", "text/plain")},
        data={"source_lang": "en", "target_lang": "de", "provider": "nope"},
    )
    assert response.status_code == 400
    assert "Unsupported provider" in response.json()["detail"]


async def seed_completed_job(factory, user, *, with_artifact: bool) -> uuid.UUID:
    """Insert a finished job, optionally with a stored output file."""
    job_id = uuid.uuid4()
    async with factory() as db:
        db.add(
            DocumentJob(
                id=job_id,
                user_id=user.id,
                original_filename="report.docx",
                file_size_bytes=2048,
                source_lang="en",
                target_lang="de",
                provider="marianmt",
                status="completed",
            )
        )
        db.add(
            DocumentResult(
                job_id=job_id,
                translated_content="Vierteljahresbericht",
                chunk_count=3,
                total_characters=42,
            )
        )
        if with_artifact:
            content = build_docx()
            db.add(
                DocumentArtifact(
                    job_id=job_id,
                    content=content,
                    filename="report-de.docx",
                    mime_type=DOCX_MIME,
                    byte_size=len(content),
                    format_preserved=True,
                    segment_count=14,
                    translated_segments=12,
                    failed_segments=0,
                )
            )
        await db.commit()
    return job_id


async def test_download_returns_the_original_file_type(api):
    client, factory, user = api
    job_id = await seed_completed_job(factory, user, with_artifact=True)

    response = await client.get(f"/api/v1/documents/jobs/{job_id}/download")

    assert response.status_code == 200
    assert response.headers["content-type"] == DOCX_MIME
    assert response.headers["content-disposition"] == 'attachment; filename="report-de.docx"'
    # A DOCX is a zip archive, and the payload must open as a real document.
    assert response.content[:2] == b"PK"

    from docx import Document

    assert Document(io.BytesIO(response.content)).paragraphs[0].text == "Quarterly Report"


async def test_job_detail_reports_format_preservation_stats(api):
    client, factory, user = api
    job_id = await seed_completed_job(factory, user, with_artifact=True)

    response = await client.get(f"/api/v1/documents/jobs/{job_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["segment_count"] == 14
    assert body["translated_segments"] == 12
    assert body["failed_segments"] == 0
    assert body["format_preserved"] is True
    assert body["output_filename"] == "report-de.docx"
    assert body["translated_preview"] == "Vierteljahresbericht"


async def test_legacy_job_without_a_stored_file_still_downloads_as_text(api):
    client, factory, user = api
    job_id = await seed_completed_job(factory, user, with_artifact=False)

    response = await client.get(f"/api/v1/documents/jobs/{job_id}/download")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert response.text == "Vierteljahresbericht"
    assert "report-translated.txt" in response.headers["content-disposition"]


async def test_deleting_a_job_removes_its_stored_file(api):
    client, factory, user = api
    job_id = await seed_completed_job(factory, user, with_artifact=True)

    response = await client.delete(f"/api/v1/documents/jobs/{job_id}")
    assert response.status_code == 204

    async with factory() as db:
        from sqlalchemy import func, select

        remaining = await db.execute(select(func.count()).select_from(DocumentArtifact))
        assert remaining.scalar() == 0


async def test_clearing_finished_jobs_removes_stored_files(api):
    client, factory, user = api
    await seed_completed_job(factory, user, with_artifact=True)
    await seed_completed_job(factory, user, with_artifact=True)

    response = await client.delete("/api/v1/documents/jobs")
    assert response.status_code == 200
    assert response.json()["deleted"] == 2

    async with factory() as db:
        from sqlalchemy import func, select

        remaining = await db.execute(select(func.count()).select_from(DocumentArtifact))
        assert remaining.scalar() == 0


async def test_download_before_completion_is_refused(api):
    client, factory, user = api
    job_id = uuid.uuid4()
    async with factory() as db:
        db.add(
            DocumentJob(
                id=job_id,
                user_id=user.id,
                original_filename="pending.docx",
                file_size_bytes=10,
                source_lang="en",
                target_lang="de",
                provider="marianmt",
                status="processing",
            )
        )
        await db.commit()

    response = await client.get(f"/api/v1/documents/jobs/{job_id}/download")
    assert response.status_code == 400
    assert "not completed" in response.json()["detail"]
