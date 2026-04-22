import time
from contextlib import asynccontextmanager
from typing import AsyncIterator

import structlog
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.shared.config import WorkerSettings
from src.shared.logging import setup_logging
from src.worker.model_cache import ModelCache
from src.worker.translator import SUPPORTED_PAIRS, translate_text

log = structlog.get_logger()
settings = WorkerSettings()

model_cache: ModelCache | None = None
start_time: float = 0


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    global model_cache, start_time
    setup_logging(settings.log_level)
    model_cache = ModelCache(
        model_dir=settings.model_dir,
        max_models=settings.model_cache_size,
    )
    start_time = time.monotonic()
    log.info("worker_started", model_dir=settings.model_dir, max_models=settings.model_cache_size)
    yield
    log.info("worker_shutdown")


app = FastAPI(title="DeepLV Model Worker", version="1.0.0", lifespan=lifespan)


class TranslateRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    source_lang: str = Field(..., min_length=2, max_length=5)
    target_lang: str = Field(..., min_length=2, max_length=5)


class TranslateResponse(BaseModel):
    translated_text: str
    source_lang: str
    target_lang: str
    pivoted: bool
    latency_ms: float


@app.post("/translate", response_model=TranslateResponse)
async def translate(req: TranslateRequest) -> TranslateResponse:
    assert model_cache is not None

    try:
        result = translate_text(
            model_cache=model_cache,
            text=req.text,
            source_lang=req.source_lang,
            target_lang=req.target_lang,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=f"Model not available: {e}") from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return TranslateResponse(**result)


@app.get("/health")
async def health() -> dict:
    assert model_cache is not None
    return {
        "status": "healthy",
        "loaded_models": model_cache.loaded_models,
        "model_count": model_cache.size,
        "uptime_seconds": round(time.monotonic() - start_time, 1),
    }


@app.get("/languages")
async def languages() -> dict:
    pairs = [{"source": s, "target": t} for s, t in sorted(SUPPORTED_PAIRS)]
    return {"supported_pairs": pairs, "total": len(pairs)}
