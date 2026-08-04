"""Email verification / OTP flow tests.

RESEND_API_KEY is unset in the test environment, so email.send_email()
no-ops (logs instead of sending) -- these tests never hit the network.
They need a real Postgres; CI's test job has none, so every test goes
through conftest.py's register_or_skip() to skip gracefully when the DB
is unreachable (mirroring test_api.py's test_register_and_login).
"""

import pytest

from src.api.database import async_session
from src.api.services import otp
from src.api.services.auth import get_user_by_email

from .conftest import register_or_skip


async def _get_raw_otp_code(email: str) -> str:
    """Issue a fresh OTP directly against the DB, bypassing HTTP (the raw
    code is never returned over the API by design)."""
    async with async_session() as db:
        user = await get_user_by_email(db, email)
        assert user is not None
        return await otp.create_otp(db, user.id)


@pytest.mark.asyncio
async def test_register_creates_unverified_user(client):
    email = "unverified@example.com"
    resp = await register_or_skip(client, email, "testpassword123")
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_login_blocked_when_unverified(client):
    email = "login-blocked@example.com"
    reg = await register_or_skip(client, email, "testpassword123")
    assert reg.status_code == 201

    resp = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "testpassword123"}
    )
    assert resp.status_code == 403
    assert resp.json()["detail"]["error"] == "email_not_verified"


@pytest.mark.asyncio
async def test_verify_email_unlocks_login(client):
    email = "verify-me@example.com"
    password = "testpassword123"
    await register_or_skip(client, email, password)

    code = await _get_raw_otp_code(email)

    verify_resp = await client.post(
        "/api/v1/auth/verify-email", json={"email": email, "code": code}
    )
    assert verify_resp.status_code == 200
    assert "access_token" in verify_resp.json()

    login_resp = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert login_resp.status_code == 200


@pytest.mark.asyncio
async def test_verify_email_rejects_wrong_code(client):
    email = "wrong-code@example.com"
    await register_or_skip(client, email, "testpassword123")

    await _get_raw_otp_code(email)  # issue a real code, then submit a wrong one

    resp = await client.post("/api/v1/auth/verify-email", json={"email": email, "code": "000000"})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_verify_email_locks_after_max_attempts(client):
    email = "brute-force@example.com"
    await register_or_skip(client, email, "testpassword123")

    code = await _get_raw_otp_code(email)

    for _ in range(otp.MAX_OTP_ATTEMPTS):
        resp = await client.post(
            "/api/v1/auth/verify-email", json={"email": email, "code": "000000"}
        )
        assert resp.status_code == 400

    # Even the correct code is now rejected -- locked out, must resend.
    locked_resp = await client.post(
        "/api/v1/auth/verify-email", json={"email": email, "code": code}
    )
    assert locked_resp.status_code == 400
    assert "too many" in locked_resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_resend_verification_rate_limited(client):
    email = "resend-spam@example.com"
    await register_or_skip(client, email, "testpassword123")

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
            return [0, 1, 999, True]  # current_count way above any max_requests

    from src.api.main import app

    app.state.redis.pipeline = lambda: _AlwaysOverLimitPipeline()

    resp = await client.post("/api/v1/auth/resend-verification", json={"email": email})
    assert resp.status_code == 429


@pytest.mark.asyncio
async def test_forgot_password_response_has_no_token(client):
    email = "forgot-me@example.com"
    await register_or_skip(client, email, "testpassword123")

    resp = await client.post("/api/v1/auth/forgot-password", json={"email": email})
    assert resp.status_code == 200
    body = resp.json()
    assert "reset_token" not in body
    assert "message" in body
