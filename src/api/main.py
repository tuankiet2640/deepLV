import time
import uuid
from contextlib import asynccontextmanager
from typing import AsyncIterator

import redis.asyncio as redis
import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from src.api.metrics import metrics_middleware, metrics_response
from src.api.middleware.rate_limit import RateLimiter
from src.api.routers import auth, health, keys, translate, usage, providers, credits
from src.api.services.cache import TranslationCache
from src.shared.config import APISettings
from src.shared.logging import setup_logging

log = structlog.get_logger()
settings = APISettings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    setup_logging(settings.log_level)

    # Create database tables on startup
    from src.api.database import engine
    from src.api.models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    log.info("database_tables_ready")

    # Initialize Redis
    redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    app.state.redis = redis_client
    app.state.translation_cache = TranslationCache(redis_client)
    app.state.rate_limiter = RateLimiter(
        redis_client,
        max_requests=settings.rate_limit_requests,
        window_seconds=settings.rate_limit_window_seconds,
    )
    app.state.settings = settings
    app.state.start_time = time.monotonic()

    log.info("api_started", port=settings.api_port)
    yield

    await redis_client.aclose()
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
    response = await call_next(request)  # type: ignore[misc]
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


# Metrics endpoint (outside /api/v1 — for Prometheus scraping)
@app.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    return metrics_response()
