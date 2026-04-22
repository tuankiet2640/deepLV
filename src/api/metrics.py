import time
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from prometheus_client import Counter, Histogram, generate_latest

REQUEST_COUNT = Counter(
    "deeplv_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

REQUEST_LATENCY = Histogram(
    "deeplv_http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

TRANSLATION_COUNT = Counter(
    "deeplv_translations_total",
    "Total translations processed",
    ["source_lang", "target_lang", "cached"],
)

CACHE_HIT = Counter(
    "deeplv_cache_hits_total",
    "Translation cache hits",
)

CACHE_MISS = Counter(
    "deeplv_cache_misses_total",
    "Translation cache misses",
)


async def metrics_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    start = time.monotonic()
    response = await call_next(request)
    elapsed = time.monotonic() - start

    path = request.url.path
    # Normalize path to avoid cardinality explosion
    if path.startswith("/api/v1/keys/"):
        path = "/api/v1/keys/{id}"

    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=path,
        status=response.status_code,
    ).inc()
    REQUEST_LATENCY.labels(method=request.method, endpoint=path).observe(elapsed)

    return response


def metrics_response() -> Response:
    return Response(content=generate_latest(), media_type="text/plain")
