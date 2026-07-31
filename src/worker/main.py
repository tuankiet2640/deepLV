import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from prometheus_client import Counter, Histogram, generate_latest
from pydantic import BaseModel, Field

from src.shared.config import WorkerSettings
from src.shared.logging import setup_logging
from src.worker.model_cache import ModelCache
from src.worker.translator import SUPPORTED_PAIRS, translate_text

log = structlog.get_logger()
settings = WorkerSettings()

model_cache: ModelCache | None = None
start_time: float = 0

# Worker-specific metrics
WORKER_MODEL_LOAD_TIME = Histogram(
    "deeplv_worker_model_load_seconds",
    "Time to load a translation model",
    ["language_pair"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
)

WORKER_INFERENCE_LATENCY = Histogram(
    "deeplv_worker_inference_seconds",
    "Translation inference latency by language pair",
    ["source_lang", "target_lang"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

WORKER_TRANSLATIONS_TOTAL = Counter(
    "deeplv_worker_translations_total",
    "Total translations processed by worker",
    ["source_lang", "target_lang"],
)

WORKER_ERRORS_TOTAL = Counter(
    "deeplv_worker_errors_total",
    "Total translation errors in worker",
    ["error_type"],
)


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
        inference_start = time.monotonic()
        result = translate_text(
            model_cache=model_cache,
            text=req.text,
            source_lang=req.source_lang,
            target_lang=req.target_lang,
        )
        inference_elapsed = time.monotonic() - inference_start
        WORKER_INFERENCE_LATENCY.labels(
            source_lang=req.source_lang, target_lang=req.target_lang
        ).observe(inference_elapsed)
        WORKER_TRANSLATIONS_TOTAL.labels(
            source_lang=req.source_lang, target_lang=req.target_lang
        ).inc()
    except FileNotFoundError as e:
        WORKER_ERRORS_TOTAL.labels(error_type="model_not_available").inc()
        raise HTTPException(status_code=503, detail=f"Model not available: {e}") from e
    except ValueError as e:
        WORKER_ERRORS_TOTAL.labels(error_type="invalid_request").inc()
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


@app.get("/metrics")
async def metrics() -> PlainTextResponse:
    """Expose Prometheus metrics for the worker service."""
    return PlainTextResponse(content=generate_latest(), media_type="text/plain")
