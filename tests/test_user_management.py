"""Account lifecycle: deactivation blocks all auth paths, reactivation restores, audited."""

import pytest

from src.api.database import async_session
from src.api.services.auth import get_user_by_email

from .conftest import register_or_skip


async def _register_verified(client, email: str, password: str = "testpassword123") -> None:
    await register_or_skip(client, email, password)
    async with async_session() as db:
        user = await get_user_by_email(db, email)
        user.is_verified = True
        await db.commit()


async def _register_admin_token(client, email: str, password: str = "testpassword123") -> str:
    await _register_verified(client, email, password)
    async with async_session() as db:
        user = await get_user_by_email(db, email)
        user.role = "admin"
        await db.commit()
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.json()
    return login.json()["access_token"]


async def _login(client, email: str, password: str = "testpassword123"):
    return await client.post("/api/v1/auth/login", json={"email": email, "password": password})


async def _user_id(email: str) -> str:
    async with async_session() as db:
        user = await get_user_by_email(db, email)
        return str(user.id)


@pytest.mark.asyncio
async def test_deactivation_blocks_login(client):
    admin_token = await _register_admin_token(client, "um-admin1@example.com")
    await _register_verified(client, "um-target1@example.com")
    target_id = await _user_id("um-target1@example.com")

    resp = await client.post(
        f"/api/v1/admin/users/{target_id}/deactivate",
        json={"reason": "abuse report"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200, resp.json()
    assert resp.json()["is_active"] is False

    login = await _login(client, "um-target1@example.com")
    assert login.status_code == 403
    assert login.json()["detail"]["error"] == "account_deactivated"


@pytest.mark.asyncio
async def test_deactivation_rejects_existing_token(client):
    admin_token = await _register_admin_token(client, "um-admin2@example.com")
    await _register_verified(client, "um-target2@example.com")

    # Target logs in and holds a valid token BEFORE being deactivated.
    login = await _login(client, "um-target2@example.com")
    assert login.status_code == 200
    target_token = login.json()["access_token"]

    # Token works right now.
    me = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {target_token}"})
    assert me.status_code == 200

    target_id = await _user_id("um-target2@example.com")
    await client.post(
        f"/api/v1/admin/users/{target_id}/deactivate",
        json={"reason": "mid-session disable"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # The still-unexpired token must now be rejected -- this is the whole point.
    me_after = await client.get(
        "/api/v1/users/me", headers={"Authorization": f"Bearer {target_token}"}
    )
    assert me_after.status_code == 403
    assert me_after.json()["detail"]["error"] == "account_deactivated"


@pytest.mark.asyncio
async def test_reactivation_restores_login(client):
    admin_token = await _register_admin_token(client, "um-admin3@example.com")
    await _register_verified(client, "um-target3@example.com")
    target_id = await _user_id("um-target3@example.com")
    headers = {"Authorization": f"Bearer {admin_token}"}

    await client.post(
        f"/api/v1/admin/users/{target_id}/deactivate",
        json={"reason": "temporary hold"},
        headers=headers,
    )
    assert (await _login(client, "um-target3@example.com")).status_code == 403

    react = await client.post(f"/api/v1/admin/users/{target_id}/reactivate", headers=headers)
    assert react.status_code == 200, react.json()
    assert react.json()["is_active"] is True
    assert react.json()["deactivation_reason"] is None

    assert (await _login(client, "um-target3@example.com")).status_code == 200


@pytest.mark.asyncio
async def test_cannot_deactivate_self(client):
    admin_token = await _register_admin_token(client, "um-admin4@example.com")
    admin_id = await _user_id("um-admin4@example.com")

    resp = await client.post(
        f"/api/v1/admin/users/{admin_id}/deactivate",
        json={"reason": "oops"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 400
    assert "own account" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_deactivate_requires_nonempty_reason(client):
    admin_token = await _register_admin_token(client, "um-admin5@example.com")
    await _register_verified(client, "um-target5@example.com")
    target_id = await _user_id("um-target5@example.com")

    resp = await client.post(
        f"/api/v1/admin/users/{target_id}/deactivate",
        json={"reason": ""},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_double_deactivate_conflicts(client):
    admin_token = await _register_admin_token(client, "um-admin6@example.com")
    await _register_verified(client, "um-target6@example.com")
    target_id = await _user_id("um-target6@example.com")
    headers = {"Authorization": f"Bearer {admin_token}"}

    first = await client.post(
        f"/api/v1/admin/users/{target_id}/deactivate",
        json={"reason": "first"},
        headers=headers,
    )
    assert first.status_code == 200
    second = await client.post(
        f"/api/v1/admin/users/{target_id}/deactivate",
        json={"reason": "again"},
        headers=headers,
    )
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_deactivation_recorded_in_audit_log(client):
    admin_token = await _register_admin_token(client, "um-admin7@example.com")
    await _register_verified(client, "um-target7@example.com")
    target_id = await _user_id("um-target7@example.com")
    headers = {"Authorization": f"Bearer {admin_token}"}

    await client.post(
        f"/api/v1/admin/users/{target_id}/deactivate",
        json={"reason": "audit-check-reason"},
        headers=headers,
    )

    audit = await client.get("/api/v1/admin/audit-log", headers=headers)
    assert audit.status_code == 200
    entry = next(
        e
        for e in audit.json()["entries"]
        if e["action"] == "user.deactivated" and e["target_id"] == target_id
    )
    assert "audit-check-reason" in entry["details"]


@pytest.mark.asyncio
async def test_status_filter_returns_only_inactive(client):
    admin_token = await _register_admin_token(client, "um-admin8@example.com")
    await _register_verified(client, "um-target8@example.com")
    target_id = await _user_id("um-target8@example.com")
    headers = {"Authorization": f"Bearer {admin_token}"}

    await client.post(
        f"/api/v1/admin/users/{target_id}/deactivate",
        json={"reason": "for filter test"},
        headers=headers,
    )

    inactive = await client.get("/api/v1/admin/users?status=inactive", headers=headers)
    assert inactive.status_code == 200
    ids = {u["id"] for u in inactive.json()["users"]}
    assert target_id in ids
    assert all(u["is_active"] is False for u in inactive.json()["users"])
