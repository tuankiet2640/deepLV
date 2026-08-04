"""Anonymous translate tier: MarianMT only, IP-rate-limited, no sign-in required."""

from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_anonymous_marianmt_translate_succeeds(client):
    with patch(
        "src.api.services.providers.marianmt.MarianMTProvider.translate",
        new=AsyncMock(return_value="Hallo Welt"),
    ):
        resp = await client.post(
            "/api/v1/translate",
            json={"text": "Hello world", "source_lang": "en", "target_lang": "de"},
        )
    assert resp.status_code == 200
    assert resp.json()["translated_text"] == "Hallo Welt"


@pytest.mark.asyncio
async def test_anonymous_non_marianmt_provider_requires_signin(client):
    resp = await client.post(
        "/api/v1/translate",
        json={
            "text": "Hello world",
            "source_lang": "en",
            "target_lang": "de",
            "provider": "openai",
        },
    )
    assert resp.status_code == 401
    assert "sign in" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_anonymous_translate_rate_limited(client):
    class _AlwaysOverLimitPipeline:
        def zremrangebyscore(self, *a):
            pass

        def zadd(self, *a):
            pass

        def zcard(self, *a):
            pass

        def expire(self, *a):
            pass

        async def execute(self):
            return [0, 1, 999, True]

    from src.api.main import app

    app.state.redis.pipeline = lambda: _AlwaysOverLimitPipeline()

    resp = await client.post(
        "/api/v1/translate",
        json={"text": "Hello world", "source_lang": "en", "target_lang": "de"},
    )
    assert resp.status_code == 429
    assert resp.headers["Retry-After"] == "3600"


@pytest.mark.asyncio
async def test_anonymous_translate_no_usage_log_written(client):
    """Anonymous requests have no user to attribute usage to -- confirm the
    background logging call is skipped (it would otherwise error on a None
    user_id, since UsageLog.user_id is a non-nullable FK)."""
    with (
        patch(
            "src.api.services.providers.marianmt.MarianMTProvider.translate",
            new=AsyncMock(return_value="Hallo Welt"),
        ),
        patch("src.api.routers.translate._log_usage") as mock_log_usage,
    ):
        resp = await client.post(
            "/api/v1/translate",
            json={"text": "Hello world", "source_lang": "en", "target_lang": "de"},
        )
    assert resp.status_code == 200
    mock_log_usage.assert_not_called()
