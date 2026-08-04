"""Shared pytest fixtures for API integration tests."""

from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def mock_redis():
    mock = AsyncMock()
    mock.ping = AsyncMock(return_value=True)
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.pipeline = lambda: _MockPipeline()
    mock.aclose = AsyncMock()
    return mock


class _MockPipeline:
    def __init__(self):
        self._commands = []

    def zremrangebyscore(self, *args):
        self._commands.append(("zremrangebyscore", args))

    def zadd(self, *args):
        self._commands.append(("zadd", args))

    def zcard(self, *args):
        self._commands.append(("zcard", args))

    def expire(self, *args):
        self._commands.append(("expire", args))

    async def execute(self):
        return [0, 1, 1, True]


@pytest.fixture
async def client(mock_redis):
    # Initialize app.state that would normally be set by lifespan
    import time

    from src.api.main import app
    from src.api.middleware.rate_limit import RateLimiter
    from src.api.services.cache import TranslationCache
    from src.shared.config import APISettings

    app.state.redis = mock_redis
    app.state.translation_cache = TranslationCache(mock_redis)
    app.state.rate_limiter = RateLimiter(mock_redis)
    app.state.settings = APISettings()
    app.state.start_time = time.monotonic()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def register_or_skip(client, email: str, password: str):
    """Register a user, skipping the test if no Postgres is reachable.

    CI runs the test job with no database service (see .github/workflows/ci.yml),
    so a real connection attempt raises OSError rather than the app returning a
    clean 500 -- this mirrors test_api.py's test_register_and_login guard.
    """
    try:
        resp = await client.post(
            "/api/v1/auth/register", json={"email": email, "password": password}
        )
    except OSError:
        pytest.skip("PostgreSQL not available")
    if resp.status_code == 500:
        pytest.skip("PostgreSQL not available")
    return resp
