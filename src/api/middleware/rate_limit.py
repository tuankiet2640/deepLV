import time

import redis.asyncio as redis
import structlog

log = structlog.get_logger()


class RateLimiter:
    """Sliding window rate limiter backed by Redis."""

    def __init__(
        self,
        redis_client: redis.Redis,
        max_requests: int = 100,
        window_seconds: int = 60,
    ):
        self._redis = redis_client
        self._max_requests = max_requests
        self._window_seconds = window_seconds

    async def check(self, identifier: str) -> tuple[bool, int]:
        """Check rate limit. Returns (allowed, remaining_requests)."""
        key = f"ratelimit:{identifier}"
        now = time.time()
        window_start = now - self._window_seconds

        pipe = self._redis.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zadd(key, {str(now): now})
        pipe.zcard(key)
        pipe.expire(key, self._window_seconds)

        try:
            results = await pipe.execute()
            current_count = results[2]
        except redis.RedisError:
            log.warning("rate_limit_redis_error", exc_info=True)
            return True, self._max_requests  # fail open

        remaining = max(0, self._max_requests - current_count)
        allowed = current_count <= self._max_requests

        if not allowed:
            log.info("rate_limit_exceeded", identifier=identifier, count=current_count)

        return allowed, remaining
