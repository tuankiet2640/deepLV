import time
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from prometheus_client import Counter, Gauge, Histogram, generate_latest

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

PROVIDER_TRANSLATION_COUNT = Counter(
    "deeplv_provider_translations_total",
    "Translations processed by provider",
    ["provider"],
)

DOCUMENT_JOBS_COUNT = Counter(
    "deeplv_document_jobs_total",
    "Document translation jobs by status",
    ["status"],
)

CREDITS_SPENT = Counter(
    "deeplv_credits_spent_total",
    "Total translation credits spent",
)

ACTIVE_PROVIDER_KEYS = Gauge(
    "deeplv_active_provider_keys",
    "Number of currently active provider API keys",
)


async def metrics_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    start = time.monotonic()
    response = await call_next(request)
    elapsed = time.monotonic() - start

    # Substitute matched path params (IDs, UUIDs) back to their "{name}"
    # placeholder so e.g. "/api/v1/admin/users/<uuid>" collapses into one
    # series per route instead of growing cardinality without bound (and,
    # since /metrics is unauthenticated, publicly leaking those IDs).
    # route.path alone isn't enough here: it only reflects the path as
    # declared on its own APIRouter, not prefixes added later via
    # app.include_router(prefix=...), so it'd silently drop "/api/v1".
    # Requests that never matched a route (404s, scanner traffic hitting
    # arbitrary paths) have the same unbounded-cardinality problem via the
    # raw path, so they're collapsed into a single bucket instead.
    route = request.scope.get("route")
    if route is None:
        endpoint = "{unmatched}"
    else:
        endpoint = request.url.path
        for name, value in request.path_params.items():
            endpoint = endpoint.replace(str(value), f"{{{name}}}", 1)

    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=endpoint,
        status=response.status_code,
    ).inc()
    REQUEST_LATENCY.labels(method=request.method, endpoint=endpoint).observe(elapsed)

    return response


def metrics_response() -> Response:
    return Response(content=generate_latest(), media_type="text/plain")
