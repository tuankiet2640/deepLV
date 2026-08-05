"""Glossary term substitution engine + CRUD + /translate integration tests."""

from unittest.mock import AsyncMock, patch

import pytest

from src.api.database import async_session
from src.api.services import glossary
from src.api.services.auth import get_user_by_email

from .conftest import register_or_skip


class _Term:
    def __init__(self, source_term, target_term, case_sensitive=False):
        self.source_term = source_term
        self.target_term = target_term
        self.case_sensitive = case_sensitive


class TestSubstituteRestore:
    def test_simple_round_trip(self):
        terms = [_Term("Acme Corp", "Acme Corporation Inc.")]
        text = "I work at Acme Corp today."
        substituted = glossary.substitute(text, terms)
        assert "Acme Corp" not in substituted
        restored = glossary.restore(substituted, terms)
        assert restored == "I work at Acme Corporation Inc. today."

    def test_punctuation_edge_cases_that_break_bare_word_boundary(self):
        # \b is broken for terms starting/ending on non-alphanumeric chars --
        # these must still match with the lookaround-based boundaries.
        cases = [
            (_Term("C++", "C++"), "I love C++ programming."),
            (_Term("C++", "C++"), "C++ is great"),
            (_Term("Acme Corp.", "Acme Corp."), "I work at Acme Corp. today"),
            (_Term("AT&T", "AT&T"), "Call AT&T support"),
        ]
        for term, text in cases:
            substituted = glossary.substitute(text, [term])
            assert substituted != text, f"failed to substitute {term.source_term!r} in {text!r}"
            restored = glossary.restore(substituted, [term])
            assert restored == text

    def test_case_insensitive_by_default(self):
        terms = [_Term("acme", "ACME")]
        text = "ACME and Acme and acme"
        restored = glossary.restore(glossary.substitute(text, terms), terms)
        assert restored == "ACME and ACME and ACME"

    def test_case_sensitive_when_flagged(self):
        terms = [_Term("Acme", "ACME-CS", case_sensitive=True)]
        text = "Acme and acme"
        restored = glossary.restore(glossary.substitute(text, terms), terms)
        assert restored == "ACME-CS and acme"

    def test_longest_term_first_avoids_partial_overlap(self):
        terms = [_Term("Acme", "SHORT"), _Term("Acme Corp", "Acme Corporation Inc.")]
        text = "I work at Acme Corp and love Acme products."
        restored = glossary.restore(glossary.substitute(text, terms), terms)
        assert restored == "I work at Acme Corporation Inc. and love SHORT products."

    def test_multiple_occurrences_of_same_term(self):
        terms = [_Term("Acme", "ACME")]
        text = "Acme makes Acme products for Acme customers."
        restored = glossary.restore(glossary.substitute(text, terms), terms)
        assert restored == "ACME makes ACME products for ACME customers."

    def test_no_terms_is_a_no_op(self):
        text = "Nothing to substitute here."
        assert glossary.substitute(text, []) == text

    def test_placeholder_not_found_is_left_alone(self):
        # If the provider mangles/drops a placeholder, restore() just
        # doesn't find it -- no crash, no corruption of the rest of the text.
        terms = [_Term("Acme", "ACME")]
        mangled_output = "some translated text with no placeholder at all"
        assert glossary.restore(mangled_output, terms) == mangled_output


@pytest.mark.asyncio
async def test_translate_applies_glossary_term(client):
    email = "glossary-translate@example.com"
    await register_or_skip(client, email, "testpassword123")

    async with async_session() as db:
        user = await get_user_by_email(db, email)

    from src.api.services import otp

    async with async_session() as db:
        code = await otp.create_otp(db, user.id)
    verify = await client.post("/api/v1/auth/verify-email", json={"email": email, "code": code})
    token = verify.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    create_resp = await client.post(
        "/api/v1/glossary",
        headers=headers,
        json={
            "source_lang": "en",
            "target_lang": "de",
            "source_term": "Acme Corp",
            "target_term": "Acme Corporation GmbH",
        },
    )
    assert create_resp.status_code == 201

    # Mocked provider echoes back whatever it was given, with placeholders
    # intact -- proves substitution happens before the provider call and
    # restoration happens after, regardless of provider.
    with patch(
        "src.api.services.providers.marianmt.MarianMTProvider.translate",
        new=AsyncMock(side_effect=lambda text, source_lang, target_lang: text),
    ):
        resp = await client.post(
            "/api/v1/translate",
            headers=headers,
            json={
                "text": "I work at Acme Corp.",
                "source_lang": "en",
                "target_lang": "de",
            },
        )
    assert resp.status_code == 200
    assert resp.json()["translated_text"] == "I work at Acme Corporation GmbH."


@pytest.mark.asyncio
async def test_anonymous_translate_unaffected_by_glossary(client):
    # No account at all -- glossary lookup must be skipped entirely.
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
async def test_cache_sharing_restores_per_user(client):
    """Two users with different glossaries for the same raw input text each
    get their own correctly restored output, even if the underlying cache
    entry (which only ever stores placeholder-templated text) is shared."""
    email_a, email_b = "glossary-user-a@example.com", "glossary-user-b@example.com"
    await register_or_skip(client, email_a, "testpassword123")
    await register_or_skip(client, email_b, "testpassword123")

    from src.api.services import otp

    async def _get_token(email: str) -> str:
        async with async_session() as db:
            user = await get_user_by_email(db, email)
            code = await otp.create_otp(db, user.id)
        verify = await client.post("/api/v1/auth/verify-email", json={"email": email, "code": code})
        return verify.json()["access_token"]

    token_a = await _get_token(email_a)
    token_b = await _get_token(email_b)

    await client.post(
        "/api/v1/glossary",
        headers={"Authorization": f"Bearer {token_a}"},
        json={
            "source_lang": "en",
            "target_lang": "de",
            "source_term": "widget",
            "target_term": "Widget-A",
        },
    )
    await client.post(
        "/api/v1/glossary",
        headers={"Authorization": f"Bearer {token_b}"},
        json={
            "source_lang": "en",
            "target_lang": "de",
            "source_term": "widget",
            "target_term": "Widget-B",
        },
    )

    with patch(
        "src.api.services.providers.marianmt.MarianMTProvider.translate",
        new=AsyncMock(side_effect=lambda text, source_lang, target_lang: text),
    ):
        resp_a = await client.post(
            "/api/v1/translate",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"text": "Buy a widget", "source_lang": "en", "target_lang": "de"},
        )
        resp_b = await client.post(
            "/api/v1/translate",
            headers={"Authorization": f"Bearer {token_b}"},
            json={"text": "Buy a widget", "source_lang": "en", "target_lang": "de"},
        )

    assert resp_a.json()["translated_text"] == "Buy a Widget-A"
    assert resp_b.json()["translated_text"] == "Buy a Widget-B"


@pytest.mark.asyncio
async def test_glossary_crud_ownership_scoping(client):
    email_a, email_b = "glossary-owner-a@example.com", "glossary-owner-b@example.com"
    await register_or_skip(client, email_a, "testpassword123")
    await register_or_skip(client, email_b, "testpassword123")

    from src.api.services import otp

    async def _get_token(email: str) -> str:
        async with async_session() as db:
            user = await get_user_by_email(db, email)
            code = await otp.create_otp(db, user.id)
        verify = await client.post("/api/v1/auth/verify-email", json={"email": email, "code": code})
        return verify.json()["access_token"]

    token_a = await _get_token(email_a)
    token_b = await _get_token(email_b)
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    create_resp = await client.post(
        "/api/v1/glossary",
        headers=headers_a,
        json={
            "source_lang": "en",
            "target_lang": "de",
            "source_term": "private term",
            "target_term": "geheimer Begriff",
        },
    )
    term_id = create_resp.json()["id"]

    # User B can't see, update, or delete user A's term
    list_resp = await client.get("/api/v1/glossary", headers=headers_b)
    assert all(t["id"] != term_id for t in list_resp.json()["terms"])

    patch_resp = await client.patch(
        f"/api/v1/glossary/{term_id}", headers=headers_b, json={"target_term": "hacked"}
    )
    assert patch_resp.status_code == 404

    delete_resp = await client.delete(f"/api/v1/glossary/{term_id}", headers=headers_b)
    assert delete_resp.status_code == 404

    # User A can update and delete their own term
    patch_own = await client.patch(
        f"/api/v1/glossary/{term_id}", headers=headers_a, json={"target_term": "updated"}
    )
    assert patch_own.status_code == 200
    assert patch_own.json()["target_term"] == "updated"

    delete_own = await client.delete(f"/api/v1/glossary/{term_id}", headers=headers_a)
    assert delete_own.status_code == 204


@pytest.mark.asyncio
async def test_glossary_rejects_duplicate(client):
    email = "glossary-dup@example.com"
    await register_or_skip(client, email, "testpassword123")

    from src.api.services import otp

    async with async_session() as db:
        user = await get_user_by_email(db, email)
        code = await otp.create_otp(db, user.id)
    verify = await client.post("/api/v1/auth/verify-email", json={"email": email, "code": code})
    headers = {"Authorization": f"Bearer {verify.json()['access_token']}"}

    payload = {
        "source_lang": "en",
        "target_lang": "de",
        "source_term": "Acme",
        "target_term": "Acme",
    }
    first = await client.post("/api/v1/glossary", headers=headers, json=payload)
    assert first.status_code == 201

    dup_payload = {**payload, "source_term": "ACME"}  # case-insensitive dup
    dup = await client.post("/api/v1/glossary", headers=headers, json=dup_payload)
    assert dup.status_code == 409
