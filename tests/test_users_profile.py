"""Profile endpoint tests: GET/PATCH /users/me, avatar upload/download/delete."""

import pytest

from src.api.database import async_session
from src.api.services import otp
from src.api.services.auth import get_user_by_email

from .conftest import register_or_skip

TINY_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108020000009077"
    "53de0000000c4944415478da6360000002000155ff8fa20000000049454e44ae426082"
)


async def _register_and_login(client, email: str, password: str = "testpassword123") -> str:
    await register_or_skip(client, email, password)

    async with async_session() as db:
        user = await get_user_by_email(db, email)
        assert user is not None
        code = await otp.create_otp(db, user.id)

    verify = await client.post("/api/v1/auth/verify-email", json={"email": email, "code": code})
    assert verify.status_code == 200
    return verify.json()["access_token"]


@pytest.mark.asyncio
async def test_get_me_returns_profile(client):
    token = await _register_and_login(client, "profile-get@example.com")

    resp = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "profile-get@example.com"
    assert body["is_verified"] is True
    assert body["has_avatar"] is False
    assert body["translation_count"] == 0
    assert body["default_source_lang"] == "auto"
    assert body["default_target_lang"] == "de"
    assert body["theme_preference"] == "system"


@pytest.mark.asyncio
async def test_patch_me_updates_preferences(client):
    token = await _register_and_login(client, "profile-patch@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.patch(
        "/api/v1/users/me",
        headers=headers,
        json={
            "display_name": "Kiet",
            "default_source_lang": "vi",
            "default_target_lang": "en",
            "theme_preference": "dark",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["display_name"] == "Kiet"
    assert body["default_source_lang"] == "vi"
    assert body["default_target_lang"] == "en"
    assert body["theme_preference"] == "dark"

    # Persisted -- a fresh GET reflects it
    get_resp = await client.get("/api/v1/users/me", headers=headers)
    assert get_resp.json()["display_name"] == "Kiet"


@pytest.mark.asyncio
async def test_patch_me_rejects_unsupported_language(client):
    token = await _register_and_login(client, "profile-badlang@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.patch(
        "/api/v1/users/me", headers=headers, json={"default_target_lang": "xx"}
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_patch_me_rejects_unsupported_theme(client):
    token = await _register_and_login(client, "profile-badtheme@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.patch(
        "/api/v1/users/me", headers=headers, json={"theme_preference": "rainbow"}
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_avatar_upload_download_delete_roundtrip(client):
    token = await _register_and_login(client, "avatar-roundtrip@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    upload_resp = await client.post(
        "/api/v1/users/me/avatar",
        headers=headers,
        files={"file": ("avatar.png", TINY_PNG, "image/png")},
    )
    assert upload_resp.status_code == 200
    assert upload_resp.json()["has_avatar"] is True

    get_resp = await client.get("/api/v1/users/me/avatar", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.content == TINY_PNG
    assert get_resp.headers["content-type"] == "image/png"

    delete_resp = await client.delete("/api/v1/users/me/avatar", headers=headers)
    assert delete_resp.status_code == 200
    assert delete_resp.json()["has_avatar"] is False

    missing_resp = await client.get("/api/v1/users/me/avatar", headers=headers)
    assert missing_resp.status_code == 404


@pytest.mark.asyncio
async def test_avatar_rejects_wrong_content_type(client):
    token = await _register_and_login(client, "avatar-badtype@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post(
        "/api/v1/users/me/avatar",
        headers=headers,
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_avatar_rejects_oversized_file(client):
    token = await _register_and_login(client, "avatar-oversized@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    oversized = b"\x00" * (2 * 1024 * 1024 + 1)
    resp = await client.post(
        "/api/v1/users/me/avatar",
        headers=headers,
        files={"file": ("avatar.png", oversized, "image/png")},
    )
    assert resp.status_code == 400
