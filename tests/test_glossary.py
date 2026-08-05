"""Glossary term substitution engine + CRUD + /translate integration tests."""

import csv
import io
import json
from unittest.mock import AsyncMock, patch

import pytest

from src.api.database import async_session
from src.api.services import glossary, otp
from src.api.services.auth import get_user_by_email

from .conftest import register_or_skip


async def _register_verify_and_get_token(
    client, email: str, password: str = "testpassword123"
) -> str:
    reg = await register_or_skip(client, email, password)
    async with async_session() as db:
        user = await get_user_by_email(db, email)
        code = await otp.create_otp(db, user.id)
    verify = await client.post("/api/v1/auth/verify-email", json={"email": email, "code": code})
    assert verify.status_code == 200, reg
    return verify.json()["access_token"]


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
    token = await _register_verify_and_get_token(client, email)
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
    token_a = await _register_verify_and_get_token(client, email_a)
    token_b = await _register_verify_and_get_token(client, email_b)

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
    token_a = await _register_verify_and_get_token(client, email_a)
    token_b = await _register_verify_and_get_token(client, email_b)
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
    token = await _register_verify_and_get_token(client, email)
    headers = {"Authorization": f"Bearer {token}"}

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


@pytest.mark.asyncio
async def test_export_json_contains_created_terms(client):
    email = "glossary-export-json@example.com"
    token = await _register_verify_and_get_token(client, email)
    headers = {"Authorization": f"Bearer {token}"}

    await client.post(
        "/api/v1/glossary",
        headers=headers,
        json={
            "source_lang": "en",
            "target_lang": "de",
            "source_term": "Acme Corp",
            "target_term": "Acme Corporation GmbH",
            "category": "legal",
            "notes": "Official registered name",
        },
    )

    resp = await client.get("/api/v1/glossary/export?format=json", headers=headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/json")
    rows = json.loads(resp.text)
    assert len(rows) == 1
    assert rows[0]["source_term"] == "Acme Corp"
    assert rows[0]["target_term"] == "Acme Corporation GmbH"
    assert rows[0]["category"] == "legal"
    assert rows[0]["notes"] == "Official registered name"
    assert "id" not in rows[0]


@pytest.mark.asyncio
async def test_export_csv_contains_created_terms(client):
    email = "glossary-export-csv@example.com"
    token = await _register_verify_and_get_token(client, email)
    headers = {"Authorization": f"Bearer {token}"}

    await client.post(
        "/api/v1/glossary",
        headers=headers,
        json={
            "source_lang": "en",
            "target_lang": "de",
            "source_term": "Acme Corp",
            "target_term": "Acme Corporation GmbH",
        },
    )

    resp = await client.get("/api/v1/glossary/export?format=csv", headers=headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    rows = list(csv.DictReader(io.StringIO(resp.text)))
    assert len(rows) == 1
    assert rows[0]["source_term"] == "Acme Corp"
    assert rows[0]["target_term"] == "Acme Corporation GmbH"


@pytest.mark.asyncio
async def test_import_json_across_users(client):
    """Exporting one user's glossary and importing it into a different
    user's account is the app's answer to team sharing (e.g. Legal sharing
    terminology with Marketing) without a shared-account/org concept."""
    email_a = "glossary-import-src@example.com"
    email_b = "glossary-import-dst@example.com"
    token_a = await _register_verify_and_get_token(client, email_a)
    token_b = await _register_verify_and_get_token(client, email_b)

    await client.post(
        "/api/v1/glossary",
        headers={"Authorization": f"Bearer {token_a}"},
        json={
            "source_lang": "en",
            "target_lang": "de",
            "source_term": "Acme Corp",
            "target_term": "Acme Corporation GmbH",
            "category": "legal",
        },
    )
    export_resp = await client.get(
        "/api/v1/glossary/export?format=json", headers={"Authorization": f"Bearer {token_a}"}
    )

    import_resp = await client.post(
        "/api/v1/glossary/import",
        headers={"Authorization": f"Bearer {token_b}"},
        files={"file": ("glossary.json", export_resp.content, "application/json")},
    )
    assert import_resp.status_code == 200
    result = import_resp.json()
    assert result["created"] == 1
    assert result["skipped_duplicate"] == 0
    assert result["errors"] == []

    list_resp = await client.get("/api/v1/glossary", headers={"Authorization": f"Bearer {token_b}"})
    terms = list_resp.json()["terms"]
    assert len(terms) == 1
    assert terms[0]["source_term"] == "Acme Corp"
    assert terms[0]["category"] == "legal"


@pytest.mark.asyncio
async def test_import_csv_round_trip(client):
    email = "glossary-import-csv@example.com"
    token = await _register_verify_and_get_token(client, email)
    headers = {"Authorization": f"Bearer {token}"}

    csv_content = (
        "source_lang,target_lang,source_term,target_term,case_sensitive,category,notes\n"
        "en,de,Acme Corp,Acme Corporation GmbH,false,legal,official name\n"
    )
    resp = await client.post(
        "/api/v1/glossary/import",
        headers=headers,
        files={"file": ("glossary.csv", csv_content.encode(), "text/csv")},
    )
    assert resp.status_code == 200
    result = resp.json()
    assert result["created"] == 1

    list_resp = await client.get("/api/v1/glossary", headers=headers)
    terms = list_resp.json()["terms"]
    assert len(terms) == 1
    assert terms[0]["source_term"] == "Acme Corp"
    assert terms[0]["category"] == "legal"


@pytest.mark.asyncio
async def test_import_partial_success(client):
    email = "glossary-import-partial@example.com"
    token = await _register_verify_and_get_token(client, email)
    headers = {"Authorization": f"Bearer {token}"}

    # Pre-existing term that the import file will also contain (duplicate).
    await client.post(
        "/api/v1/glossary",
        headers=headers,
        json={
            "source_lang": "en",
            "target_lang": "de",
            "source_term": "Existing",
            "target_term": "Vorhanden",
        },
    )

    payload = json.dumps(
        [
            {
                "source_lang": "en",
                "target_lang": "de",
                "source_term": "New Term",
                "target_term": "Neuer Begriff",
            },
            {
                "source_lang": "en",
                "target_lang": "de",
                "source_term": "Existing",
                "target_term": "Should Be Skipped",
            },
            {
                "source_lang": "xx",
                "target_lang": "de",
                "source_term": "Bad Lang",
                "target_term": "Schlecht",
            },
            {
                "source_lang": "en",
                "target_lang": "de",
                "source_term": "",
                "target_term": "Empty source",
            },
        ]
    )
    resp = await client.post(
        "/api/v1/glossary/import",
        headers=headers,
        files={"file": ("glossary.json", payload.encode(), "application/json")},
    )
    assert resp.status_code == 200
    result = resp.json()
    assert result["created"] == 1
    assert result["skipped_duplicate"] == 1
    assert len(result["errors"]) == 2

    list_resp = await client.get("/api/v1/glossary", headers=headers)
    terms = {t["source_term"] for t in list_resp.json()["terms"]}
    assert terms == {"Existing", "New Term"}


@pytest.mark.asyncio
async def test_import_rejects_unsupported_file_extension(client):
    email = "glossary-import-badext@example.com"
    token = await _register_verify_and_get_token(client, email)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post(
        "/api/v1/glossary/import",
        headers=headers,
        files={"file": ("glossary.txt", b"whatever", "text/plain")},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_import_enforces_per_user_cap(client):
    email = "glossary-import-cap@example.com"
    token = await _register_verify_and_get_token(client, email)
    headers = {"Authorization": f"Bearer {token}"}

    async with async_session() as db:
        user = await get_user_by_email(db, email)
        near_cap = glossary.MAX_TERMS_PER_USER - 1
        db.add_all(
            [
                glossary.GlossaryTerm(
                    user_id=user.id,
                    source_lang="en",
                    target_lang="de",
                    source_term=f"bulk-term-{i}",
                    target_term=f"bulk-target-{i}",
                )
                for i in range(near_cap)
            ]
        )
        await db.commit()

    payload = json.dumps(
        [
            {
                "source_lang": "en",
                "target_lang": "de",
                "source_term": "cap-1",
                "target_term": "kappe-1",
            },
            {
                "source_lang": "en",
                "target_lang": "de",
                "source_term": "cap-2",
                "target_term": "kappe-2",
            },
            {
                "source_lang": "en",
                "target_lang": "de",
                "source_term": "cap-3",
                "target_term": "kappe-3",
            },
        ]
    )
    resp = await client.post(
        "/api/v1/glossary/import",
        headers=headers,
        files={"file": ("glossary.json", payload.encode(), "application/json")},
    )
    assert resp.status_code == 200
    result = resp.json()
    assert result["created"] == 1
    assert result["skipped_cap"] == 2
