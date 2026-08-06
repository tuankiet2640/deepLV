"""Weighted per-provider credit system: rates, deduction, refunds, settings wiring."""

import pytest

from src.api.database import async_session
from src.api.services.auth import get_user_by_email
from src.api.services.provider_manager import PROVIDER_INFO, ProviderManager, get_provider_rate
from src.shared.config import APISettings

from .conftest import register_or_skip


async def _register_admin_and_get_token(
    client, email: str, password: str = "testpassword123"
) -> str:
    """Register a user, promote to admin directly, and log in.

    Only the actual first user registered in the whole test run gets
    auto-promoted to admin (see auth.py's is_first_user bootstrap) -- other
    test files register users earlier in collection order, so this sets
    the role directly instead of relying on being first.
    """
    await register_or_skip(client, email, password)
    async with async_session() as db:
        user = await get_user_by_email(db, email)
        user.is_verified = True
        user.role = "admin"
        await db.commit()
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.json()
    return login.json()["access_token"]


@pytest.mark.asyncio
async def test_provider_rates_default_to_provider_info(client):
    # This is the first DB-touching call in the file, so it needs the same
    # OSError guard register_or_skip applies elsewhere -- a real connection
    # failure (no Postgres in CI) raises OSError here rather than the app
    # returning a 500, since there's no request body to trigger validation
    # first.
    try:
        resp = await client.get("/api/v1/providers")
    except OSError:
        pytest.skip("PostgreSQL not available")
    if resp.status_code == 500:
        pytest.skip("PostgreSQL not available")
    rates = {p["name"]: p["credit_cost_per_1k_chars"] for p in resp.json()["providers"]}
    expected = {p["name"]: float(p["credit_cost_per_1k_chars"]) for p in PROVIDER_INFO}
    assert rates == expected


@pytest.mark.asyncio
async def test_admin_can_override_provider_rate_and_providers_endpoint_reflects_it(client):
    token = await _register_admin_and_get_token(client, "credits-rate-admin@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.patch(
        "/api/v1/admin/settings",
        json={"settings": {"credit_cost_per_1k_chars_openai": "12.5"}},
        headers=headers,
    )
    assert resp.status_code == 200, resp.json()

    resp = await client.get("/api/v1/providers")
    rates = {p["name"]: p["credit_cost_per_1k_chars"] for p in resp.json()["providers"]}
    assert rates["openai"] == 12.5
    assert rates["google"] == 3.0  # unaffected by the openai-only override


@pytest.mark.asyncio
async def test_free_tier_daily_chars_no_longer_exposed(client):
    token = await _register_admin_and_get_token(client, "credits-hidden-setting@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.get("/api/v1/admin/settings", headers=headers)
    keys = {s["key"] for s in resp.json()["settings"]}
    assert "free_tier_daily_chars" not in keys


@pytest.mark.asyncio
async def test_deduct_credits_charges_weighted_rate_and_records_structured_fields(client):
    token = await _register_admin_and_get_token(client, "credits-deduct@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    await client.patch(
        "/api/v1/admin/settings",
        json={"settings": {"credit_cost_per_1k_chars_google": "4.0"}},
        headers=headers,
    )
    await client.post("/api/v1/credits/purchase", json={"amount": 100}, headers=headers)

    async with async_session() as db:
        user = await get_user_by_email(db, "credits-deduct@example.com")
        pm = ProviderManager(APISettings())

        rate = await get_provider_rate(db, "google")
        assert rate == 4.0

        charged = await pm.deduct_credits(
            user=user,
            db=db,
            provider_name="google",
            char_count=2000,
            source_lang="en",
            target_lang="vi",
        )
        await db.commit()
        assert charged == 8.0  # (2000/1000) * 4.0
        await db.refresh(user)
        assert user.credits_balance == pytest.approx(92.0)

    resp = await client.get("/api/v1/credits/transactions", headers=headers)
    debit = next(t for t in resp.json()["transactions"] if t["transaction_type"] == "debit")
    assert debit["provider"] == "google"
    assert debit["char_count"] == 2000
    assert debit["rate_applied"] == 4.0
    assert debit["source_lang"] == "en"
    assert debit["target_lang"] == "vi"
    assert debit["amount"] == -8.0


@pytest.mark.asyncio
async def test_deduct_credits_returns_none_when_balance_insufficient(client):
    await _register_admin_and_get_token(client, "credits-insufficient@example.com")

    async with async_session() as db:
        user = await get_user_by_email(db, "credits-insufficient@example.com")
        balance_before = user.credits_balance
        pm = ProviderManager(APISettings())

        result = await pm.deduct_credits(
            user=user, db=db, provider_name="openai", char_count=1_000_000
        )
        await db.commit()
        assert result is None
        await db.refresh(user)
        assert user.credits_balance == balance_before


@pytest.mark.asyncio
async def test_refund_credits_restores_balance_and_records_refund(client):
    token = await _register_admin_and_get_token(client, "credits-refund@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    await client.post("/api/v1/credits/purchase", json={"amount": 100}, headers=headers)

    async with async_session() as db:
        user = await get_user_by_email(db, "credits-refund@example.com")
        pm = ProviderManager(APISettings())

        charged = await pm.deduct_credits(
            user=user, db=db, provider_name="huggingface", char_count=1000
        )
        await db.commit()
        await db.refresh(user)
        balance_after_charge = user.credits_balance

        await pm.refund_credits(
            user=user,
            db=db,
            amount=charged,
            provider_name="huggingface",
            reason="test job failed after credits were reserved",
        )
        await db.commit()
        await db.refresh(user)
        assert user.credits_balance == pytest.approx(balance_after_charge + charged)
        assert user.credits_balance == pytest.approx(100.0)

    resp = await client.get("/api/v1/credits/transactions", headers=headers)
    refund = next(t for t in resp.json()["transactions"] if t["transaction_type"] == "refund")
    assert refund["provider"] == "huggingface"
    assert refund["amount"] == pytest.approx(charged)
