import asyncio
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC
from pathlib import Path

import redis.asyncio as redis
import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.api.metrics import metrics_middleware, metrics_response
from src.api.middleware.rate_limit import RateLimiter
from src.api.routers import (
    admin,
    auth,
    credits,
    documents,
    health,
    keys,
    providers,
    translate,
    usage,
)
from src.api.services.cache import TranslationCache
from src.shared.config import APISettings
from src.shared.logging import setup_logging

log = structlog.get_logger()
settings = APISettings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    setup_logging(settings.log_level)

    # Create database tables on startup (with retry for cold starts / paused DBs)
    from src.api.database import engine
    from src.api.models import Base

    db_ready = False
    for attempt in range(5):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            log.info("database_tables_ready")
            db_ready = True
            break
        except Exception as e:
            wait = 2 ** (attempt + 1)
            log.warning("database_connect_retry", attempt=attempt + 1, wait=wait, error=str(e))
            await asyncio.sleep(wait)

    if not db_ready:
        log.error(
            "database_unavailable",
            msg="Could not connect after 5 attempts. App will start degraded.",
        )

    # Sweep orphaned document jobs stuck in "processing" state
    if db_ready:
        try:
            from datetime import datetime

            from sqlalchemy import update

            from src.api.database import async_session as session_factory
            from src.api.models.document_job import DocumentJob

            async with session_factory() as session:
                result = await session.execute(
                    update(DocumentJob)
                    .where(DocumentJob.status.in_(["processing", "pending"]))
                    .values(
                        status="failed",
                        error_message="Job interrupted by server restart",
                        completed_at=datetime.now(UTC),
                    )
                )
                if result.rowcount > 0:
                    await session.commit()
                    log.warning("orphaned_jobs_recovered", count=result.rowcount)
                else:
                    await session.commit()
        except Exception as e:
            log.warning("orphaned_jobs_cleanup_failed", error=str(e))

    # Initialize Redis (optional — app works without it, just no caching/rate-limiting)
    try:
        redis_client = redis.from_url(settings.redis_url, decode_responses=True)
        await redis_client.ping()
        app.state.redis = redis_client
        app.state.translation_cache = TranslationCache(redis_client)
        app.state.rate_limiter = RateLimiter(
            redis_client,
            max_requests=settings.rate_limit_requests,
            window_seconds=settings.rate_limit_window_seconds,
        )
        log.info("redis_connected")
    except Exception:
        log.warning("redis_unavailable", msg="Running without cache and rate limiting")
        app.state.redis = None
        app.state.translation_cache = None
        app.state.rate_limiter = None

    app.state.settings = settings
    app.state.start_time = time.monotonic()

    log.info("api_started", port=settings.api_port)
    yield

    if app.state.redis:
        await app.state.redis.aclose()
    log.info("api_shutdown")


app = FastAPI(
    title="DeepLV Translation API",
    description="Production-grade machine translation system",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request ID middleware
@app.middleware("http")
async def request_id_middleware(request: Request, call_next: object) -> Response:
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)
    response = await call_next(request)  # type: ignore[operator]
    response.headers["X-Request-ID"] = request_id
    return response


# Metrics middleware
app.middleware("http")(metrics_middleware)

# Routers
app.include_router(health.router)
app.include_router(auth.router, prefix="/api/v1")
app.include_router(keys.router, prefix="/api/v1")
app.include_router(translate.router, prefix="/api/v1")
app.include_router(usage.router, prefix="/api/v1")
app.include_router(providers.router, prefix="/api/v1")
app.include_router(credits.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")


# Metrics endpoint (outside /api/v1 — for Prometheus scraping)
@app.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    return metrics_response()


# --- Static frontend serving (for Railway/single-container deployment) ---
_static_dir = Path(__file__).parent.parent.parent / "static"
if _static_dir.exists():
    # Serve static assets (JS, CSS, images)
    app.mount("/assets", StaticFiles(directory=str(_static_dir / "assets")), name="static-assets")

    # SPA catch-all: serve index.html for any non-API route
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str) -> FileResponse:
        """Serve the React SPA for all non-API routes."""
        file_path = _static_dir / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(_static_dir / "index.html"))
