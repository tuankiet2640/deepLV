"""Regression test for the document download Content-Disposition header.

Production crashed with a 500 (UnicodeEncodeError: 'latin-1' codec can't
encode ...) whenever a translated document's original filename contained
non-ASCII characters (e.g. Vietnamese diacritics), because the raw filename
was placed directly into the Content-Disposition header value, and HTTP
headers must be latin-1 encodable.
"""

from urllib.parse import quote

from fastapi.responses import PlainTextResponse


def build_download_headers(download_filename: str) -> dict[str, str]:
    """Mirror the header-building logic in documents.download_translated_document."""
    ascii_filename = download_filename.encode("ascii", "ignore").decode("ascii") or "download.txt"
    encoded_filename = quote(download_filename)
    return {
        "Content-Disposition": (
            f"attachment; filename=\"{ascii_filename}\"; filename*=UTF-8''{encoded_filename}"
        ),
    }


def test_non_ascii_filename_does_not_crash_response_headers():
    download_filename = "Đề cương chi tiết-translated.txt"

    headers = build_download_headers(download_filename)

    # This is exactly what Starlette does internally when building the raw
    # ASGI response; it previously raised UnicodeEncodeError for this input.
    response = PlainTextResponse(content="hello", headers=headers)
    raw_headers = response.raw_headers
    assert any(k == b"content-disposition" for k, _ in raw_headers)


def test_non_ascii_filename_preserved_via_filename_star():
    download_filename = "Đề cương chi tiết-translated.txt"

    headers = build_download_headers(download_filename)

    assert "filename*=UTF-8''" in headers["Content-Disposition"]
    assert quote(download_filename) in headers["Content-Disposition"]


def test_ascii_filename_unaffected():
    download_filename = "report-translated.txt"

    headers = build_download_headers(download_filename)

    assert 'filename="report-translated.txt"' in headers["Content-Disposition"]
