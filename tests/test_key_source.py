"""Key-source selection: users can force admin credits over their own stored key."""

import pytest

from src.api.database import async_session
from src.api.models.admin_provider_key import AdminProviderKey
from src.api.models.provider_key import ProviderKey
from src.api.services.auth import get_user_by_email
from src.api.services.encryption import encrypt_api_key
from src.api.services.provider_manager import ProviderManager
from src.shared.config import APISettings

from .conftest import register_or_skip


async def _setup_user_with_keys(client, email: str) -> tuple[str, str]:
    """Register a user, give them a stored openai key and an admin openai key.

    Returns (user_id, own_key_id).
    """
    await register_or_skip(client, email, "testpassword123")
    async with async_session() as db:
        user = await get_user_by_email(db, email)
        own = ProviderKey(
            user_id=user.id,
            provider="openai",
            encrypted_api_key=encrypt_api_key("sk-user-key"),
            label="my key",
        )
        db.add(own)
        db.add(
            AdminProviderKey(
                provider="openai",
                encrypted_api_key=encrypt_api_key("sk-admin-key"),
                is_active=True,
            )
        )
        await db.commit()
        await db.refresh(own)
        return str(user.id), str(own.id)


async def _get_user(email: str):
    async with async_session() as db:
        return await get_user_by_email(db, email)


@pytest.mark.asyncio
async def test_auto_prefers_own_key(client):
    await _setup_user_with_keys(client, "ks-auto@example.com")
    pm = ProviderManager(APISettings())
    async with async_session() as db:
        user = await get_user_by_email(db, "ks-auto@example.com")
        resolved = await pm.resolve("openai", user, db)  # key_source defaults to auto
        assert resolved.used_own_key is True


@pytest.mark.asyncio
async def test_admin_source_forces_credits_despite_own_key(client):
    await _setup_user_with_keys(client, "ks-admin@example.com")
    pm = ProviderManager(APISettings())
    async with async_session() as db:
        user = await get_user_by_email(db, "ks-admin@example.com")
        resolved = await pm.resolve("openai", user, db, key_source="admin")
        # The whole point: the user HAS a key, but explicitly opted into credits.
        assert resolved.used_own_key is False


@pytest.mark.asyncio
async def test_specific_key_id_wins_over_admin_source(client):
    _, own_key_id = await _setup_user_with_keys(client, "ks-specific@example.com")
    pm = ProviderManager(APISettings())
    async with async_session() as db:
        user = await get_user_by_email(db, "ks-specific@example.com")
        resolved = await pm.resolve(
            "openai", user, db, provider_key_id=own_key_id, key_source="admin"
        )
        # An explicitly named own key beats key_source=admin.
        assert resolved.used_own_key is True


@pytest.mark.asyncio
async def test_translate_response_reports_key_source(client):
    """End-to-end: /translate echoes used_own_key so the UI can confirm the source."""
    email = "ks-response@example.com"
    await register_or_skip(client, email, "testpassword123")
    async with async_session() as db:
        user = await get_user_by_email(db, email)
        user.is_verified = True
        db.add(
            ProviderKey(
                user_id=user.id,
                provider="openai",
                encrypted_api_key=encrypt_api_key("sk-user-key"),
                label="my key",
            )
        )
        db.add(
            AdminProviderKey(
                provider="openai",
                encrypted_api_key=encrypt_api_key("sk-admin-key"),
                is_active=True,
            )
        )
        await db.commit()

    login = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "testpassword123"}
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # marianmt path is always free / not own-key; just assert the field is present
    # and typed. (Real provider calls would need network, so this asserts the
    # contract shape, which is what the UI depends on.)
    resp = await client.post(
        "/api/v1/translate",
        json={"text": "hello", "source_lang": "en", "target_lang": "de", "provider": "marianmt"},
        headers=headers,
    )
    if resp.status_code == 503:
        pytest.skip("MarianMT worker not reachable in this environment")
    assert resp.status_code == 200, resp.json()
    assert "used_own_key" in resp.json()
