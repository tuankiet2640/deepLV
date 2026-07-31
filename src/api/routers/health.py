import time

import httpx
import structlog
from fastapi import APIRouter, Request
from pydantic import BaseModel

log = structlog.get_logger()
router = APIRouter(tags=["system"])


class ServiceStatus(BaseModel):
    redis: str
    postgres: str
    model_worker: str


class HealthResponse(BaseModel):
    status: str
    services: ServiceStatus
    version: str
    uptime_seconds: float


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    redis_status = "disconnected"
    pg_status = "disconnected"
    worker_status = "disconnected"

    # Check Redis
    try:
        redis_client = request.app.state.redis
        await redis_client.ping()
        redis_status = "connected"
    except Exception:
        log.warning("health_redis_failed", exc_info=True)

    # Check PostgreSQL
    try:
        from src.api.database import engine

        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        pg_status = "connected"
    except Exception:
        log.warning("health_pg_failed", exc_info=True)

    # Check Model Worker
    try:
        worker_url = request.app.state.settings.model_worker_url
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{worker_url}/health")
            if resp.status_code == 200:
                worker_status = "connected"
    except Exception:
        log.warning("health_worker_failed", exc_info=True)

    services = ServiceStatus(redis=redis_status, postgres=pg_status, model_worker=worker_status)
    overall = (
        "healthy"
        if all(s == "connected" for s in [redis_status, pg_status, worker_status])
        else "degraded"
    )

    return HealthResponse(
        status=overall,
        services=services,
        version="1.0.0",
        uptime_seconds=round(time.monotonic() - request.app.state.start_time, 1),
    )
