"""Tests for the Resend-backed email service.

The service must never raise (a Resend outage can't be allowed to block
registration or password reset), and must no-op (log instead of send)
when RESEND_API_KEY isn't configured -- the local-dev path.
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.api.services import email


@pytest.fixture(autouse=True)
def reset_settings():
    original_key = email.settings.resend_api_key
    yield
    email.settings.resend_api_key = original_key


@pytest.mark.asyncio
async def test_send_email_noop_when_unconfigured():
    email.settings.resend_api_key = ""

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        result = await email.send_email("user@example.com", "Subject", "<p>Hi</p>")

    assert result is False
    mock_post.assert_not_called()


@pytest.mark.asyncio
async def test_send_email_posts_to_resend_when_configured():
    email.settings.resend_api_key = "re_test_key"

    mock_response = AsyncMock()
    mock_response.status_code = 200

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        result = await email.send_email("user@example.com", "Subject", "<p>Hi</p>")

    assert result is True
    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    assert args[0] == email.RESEND_API_URL
    assert kwargs["headers"]["Authorization"] == "Bearer re_test_key"
    assert kwargs["json"]["to"] == ["user@example.com"]
    assert kwargs["json"]["subject"] == "Subject"


@pytest.mark.asyncio
async def test_send_email_returns_false_on_non_2xx():
    email.settings.resend_api_key = "re_test_key"

    mock_response = AsyncMock()
    mock_response.status_code = 422
    mock_response.text = "validation error"

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        result = await email.send_email("user@example.com", "Subject", "<p>Hi</p>")

    assert result is False


@pytest.mark.asyncio
async def test_send_email_returns_false_on_http_error():
    import httpx

    email.settings.resend_api_key = "re_test_key"

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.ConnectError("boom")
        result = await email.send_email("user@example.com", "Subject", "<p>Hi</p>")

    assert result is False


@pytest.mark.asyncio
async def test_send_verification_email_includes_code():
    email.settings.resend_api_key = "re_test_key"

    mock_response = AsyncMock()
    mock_response.status_code = 200

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        await email.send_verification_email("user@example.com", "123456")

    _, kwargs = mock_post.call_args
    assert "123456" in kwargs["json"]["html"]


@pytest.mark.asyncio
async def test_send_password_reset_email_includes_link():
    email.settings.resend_api_key = "re_test_key"

    mock_response = AsyncMock()
    mock_response.status_code = 200

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        await email.send_password_reset_email(
            "user@example.com", "https://app.example.com/reset-password?token=abc"
        )

    _, kwargs = mock_post.call_args
    assert "https://app.example.com/reset-password?token=abc" in kwargs["json"]["html"]
