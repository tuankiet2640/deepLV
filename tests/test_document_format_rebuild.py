"""Tests for format-preserving document translation output.

Covers the paragraph-level parsing/rebuild helpers in DocumentParser and the
DocumentTranslator orchestration that ties per-paragraph translation back
into a DOCX/PDF rebuild (or a graceful fallback to plain text).
"""

import io
from unittest.mock import AsyncMock, MagicMock

import pytest
from docx import Document
from pypdf import PdfReader

from src.api.models.document_job import DocumentJob
from src.api.models.user import User
from src.api.services.document_parser import DocumentParser
from src.api.services.document_translator import DocumentTranslator
from src.api.services.provider_manager import ResolvedProvider


def _make_docx_bytes(paragraphs: list[tuple[str, bool]]) -> bytes:
    """Build a DOCX with the given (text, bold) paragraphs."""
    doc = Document()
    for text, bold in paragraphs:
        para = doc.add_paragraph()
        run = para.add_run(text)
        run.bold = bold
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _make_docx_with_table(paragraph_text: str, table_rows: list[list[str]]) -> bytes:
    """Build a DOCX with one top-level paragraph followed by a table."""
    doc = Document()
    doc.add_paragraph(paragraph_text)
    table = doc.add_table(rows=len(table_rows), cols=len(table_rows[0]))
    for r, row in enumerate(table_rows):
        for c, text in enumerate(row):
            table.cell(r, c).text = text
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


class TestParseParagraphs:
    def test_docx_paragraphs_are_non_empty_and_in_order(self):
        original = _make_docx_bytes([("First", False), ("", False), ("Second", True)])
        parser = DocumentParser()

        paragraphs = parser.parse_paragraphs(original, "doc.docx")

        assert paragraphs == ["First", "Second"]

    def test_docx_table_cells_are_included_after_body_paragraphs(self):
        original = _make_docx_with_table(
            "Intro paragraph",
            [["Ten", "Nguyen Van A"], ["Chuc vu", "Ky su phan mem"]],
        )
        parser = DocumentParser()

        paragraphs = parser.parse_paragraphs(original, "doc.docx")

        assert paragraphs == [
            "Intro paragraph",
            "Ten",
            "Nguyen Van A",
            "Chuc vu",
            "Ky su phan mem",
        ]

    def test_txt_splits_on_blank_lines(self):
        parser = DocumentParser()
        content = b"Para one.\n\nPara two."

        paragraphs = parser.parse_paragraphs(content, "file.txt")

        assert paragraphs == ["Para one.", "Para two."]

    def test_txt_without_blank_lines_is_single_paragraph(self):
        parser = DocumentParser()
        content = b"Just one block of text."

        paragraphs = parser.parse_paragraphs(content, "file.txt")

        assert paragraphs == ["Just one block of text."]


class TestBuildTranslatedDocx:
    def test_replaces_text_and_preserves_bold_formatting(self):
        original = _make_docx_bytes([("Xin chao", False), ("In dam", True)])
        parser = DocumentParser()

        rebuilt = parser.build_translated_docx(original, ["Hello", "Bold"])

        doc = Document(io.BytesIO(rebuilt))
        texts = [p.text for p in doc.paragraphs]
        bolds = [p.runs[0].bold if p.runs else None for p in doc.paragraphs]
        assert texts == ["Hello", "Bold"]
        assert bolds == [False, True]

    def test_extra_translated_paragraphs_are_ignored(self):
        original = _make_docx_bytes([("Only one", False)])
        parser = DocumentParser()

        # More translated entries than original non-empty paragraphs should
        # not raise or corrupt the document.
        rebuilt = parser.build_translated_docx(original, ["Translated", "Unused"])

        doc = Document(io.BytesIO(rebuilt))
        assert [p.text for p in doc.paragraphs] == ["Translated"]

    def test_table_cells_are_translated_not_left_in_original_language(self):
        original = _make_docx_with_table(
            "Intro paragraph",
            [["Ten", "Nguyen Van A"], ["Chuc vu", "Ky su phan mem"]],
        )
        parser = DocumentParser()
        translated = [
            "Introduction",
            "Name",
            "Nguyen Van A (translated)",
            "Position",
            "Software Engineer",
        ]

        rebuilt = parser.build_translated_docx(original, translated)

        doc = Document(io.BytesIO(rebuilt))
        assert doc.paragraphs[0].text == "Introduction"
        table = doc.tables[0]
        assert table.cell(0, 0).text == "Name"
        assert table.cell(0, 1).text == "Nguyen Van A (translated)"
        assert table.cell(1, 0).text == "Position"
        assert table.cell(1, 1).text == "Software Engineer"


class TestBuildTranslatedPdf:
    def test_produces_valid_pdf_with_translated_text(self):
        parser = DocumentParser()

        pdf_bytes = parser.build_translated_pdf(["Hello world.", "Second paragraph & more."])

        assert pdf_bytes.startswith(b"%PDF-")
        reader = PdfReader(io.BytesIO(pdf_bytes))
        extracted = reader.pages[0].extract_text()
        assert "Hello world." in extracted
        assert "Second paragraph & more." in extracted

    def test_vietnamese_text_renders_without_tofu_boxes(self):
        # Reportlab's default Helvetica only covers WinAnsi/Latin-1, so
        # Vietnamese diacritics used to come out as "�"/"■" tofu
        # boxes. build_translated_pdf must embed a Unicode-capable font.
        parser = DocumentParser()
        vietnamese_text = "NGUYỄN THỊ THU UYÊN - Đinh Ngọc Mai, Vũ Thanh Hằng"

        pdf_bytes = parser.build_translated_pdf([vietnamese_text])

        reader = PdfReader(io.BytesIO(pdf_bytes))
        extracted = reader.pages[0].extract_text()
        assert "�" not in extracted
        assert "■" not in extracted
        assert vietnamese_text in extracted


@pytest.fixture
def fake_provider():
    provider = MagicMock()
    provider.translate = AsyncMock(side_effect=lambda text, source_lang, target_lang: f"[{text}]")
    return provider


@pytest.fixture
def fake_provider_manager(fake_provider):
    manager = MagicMock()
    manager.resolve = AsyncMock(
        return_value=ResolvedProvider(provider=fake_provider, used_own_key=True)
    )
    manager.deduct_credits = AsyncMock(return_value=True)
    return manager


@pytest.fixture
def fake_db():
    db = MagicMock()
    db.commit = AsyncMock()
    db.added = []
    db.add = MagicMock(side_effect=lambda obj: db.added.append(obj))
    return db


def _make_job(filename: str) -> DocumentJob:
    job = DocumentJob(
        original_filename=filename,
        file_size_bytes=100,
        source_lang="vi",
        target_lang="en",
        provider="openai",
        status="pending",
    )
    return job


class TestDocumentTranslator:
    async def test_docx_job_rebuilds_format_preserving_output(self, fake_provider_manager, fake_db):
        parser = DocumentParser()
        translator = DocumentTranslator(fake_provider_manager, parser)
        original = _make_docx_bytes([("Xin chao", False)])
        job = _make_job("greeting.docx")
        user = User(email="u@example.com", password_hash="x")

        await translator.translate_document(
            job=job,
            paragraphs=["Xin chao"],
            original_file_bytes=original,
            user=user,
            db=fake_db,
        )

        assert job.status == "completed"
        result = fake_db.added[0]
        assert result.output_format == "docx"
        assert result.translated_file_bytes is not None
        doc = Document(io.BytesIO(result.translated_file_bytes))
        assert doc.paragraphs[0].text == "[Xin chao]"

    async def test_txt_job_has_no_binary_output(self, fake_provider_manager, fake_db):
        parser = DocumentParser()
        translator = DocumentTranslator(fake_provider_manager, parser)
        job = _make_job("notes.txt")
        user = User(email="u@example.com", password_hash="x")

        await translator.translate_document(
            job=job,
            paragraphs=["Hello", "World"],
            original_file_bytes=b"Hello\n\nWorld",
            user=user,
            db=fake_db,
        )

        assert job.status == "completed"
        result = fake_db.added[0]
        assert result.output_format == "txt"
        assert result.translated_file_bytes is None
        assert result.translated_content == "[Hello]\n\n[World]"

    async def test_docx_rebuild_failure_falls_back_to_txt(self, fake_provider_manager, fake_db):
        parser = DocumentParser()
        # Not a real docx, so build_translated_docx will raise internally.
        translator = DocumentTranslator(fake_provider_manager, parser)
        job = _make_job("broken.docx")
        user = User(email="u@example.com", password_hash="x")

        await translator.translate_document(
            job=job,
            paragraphs=["Xin chao"],
            original_file_bytes=b"not a real docx",
            user=user,
            db=fake_db,
        )

        # Job should still complete; rebuild failure degrades gracefully.
        assert job.status == "completed"
        result = fake_db.added[0]
        assert result.output_format == "txt"
        assert result.translated_file_bytes is None

    async def test_one_paragraph_failure_does_not_fail_whole_job(
        self, fake_provider_manager, fake_db
    ):
        provider = fake_provider_manager.resolve.return_value.provider

        async def flaky_translate(text, source_lang, target_lang):
            if text == "bad":
                raise RuntimeError("provider exploded")
            return f"[{text}]"

        provider.translate = AsyncMock(side_effect=flaky_translate)

        parser = DocumentParser()
        translator = DocumentTranslator(fake_provider_manager, parser)
        job = _make_job("notes.txt")
        user = User(email="u@example.com", password_hash="x")

        await translator.translate_document(
            job=job,
            paragraphs=["good", "bad"],
            original_file_bytes=b"good\n\nbad",
            user=user,
            db=fake_db,
        )

        assert job.status == "completed"
        result = fake_db.added[0]
        assert "[good]" in result.translated_content
        assert "Translation error in section 2" in result.translated_content
