"""DOCX handler.

Works on the XML rather than the python-docx convenience API. Every piece of
visible text in a Word document lives in a ``w:t`` node somewhere under a ``w:p``,
so one traversal of ``w:p`` elements per part reaches body text, nested tables,
text boxes, shape captions, hyperlinks and tracked insertions without a special
case for each. Headers, footers, footnotes and endnotes are separate package
parts and are walked the same way.
"""

import io
from collections.abc import Iterator
from typing import Any

from src.api.services.document_format.base import (
    DocumentFormatError,
    FormatHandler,
    TextUnit,
)
from src.api.services.document_format.oxml import (
    OoxmlTextRow,
    RowSpec,
    paragraph_rows,
    w,
)

W_P = w("p")
W_RPR = w("rPr")
W_LANG = w("lang")

DOCX_SPEC = RowSpec(
    paragraph=W_P,
    run=w("r"),
    text=w("t"),
    run_props=W_RPR,
    breaks=frozenset({w("br"), w("tab"), w("cr"), w("ptab")}),
    # Field instruction codes drive Word's recalculation and deleted revisions
    # are not visible content, so neither may be translated.
    skip=frozenset({w("instrText"), w("delText"), w("del"), w("proofErr")}),
    ignored_props=frozenset({W_LANG, w("noProof"), w("rPrChange"), w("rStyle")}),
)

_TEXT_PART_TYPES = (
    "wordprocessingml.document.main+xml",
    "wordprocessingml.header+xml",
    "wordprocessingml.footer+xml",
    "wordprocessingml.footnotes+xml",
    "wordprocessingml.endnotes+xml",
)
_MAIN_PART_TYPE = "wordprocessingml.document.main+xml"


class _DocxRow(OoxmlTextRow):
    def __init__(self, nodes: list[Any], context: str, target_lang: str) -> None:
        super().__init__(nodes, context, DOCX_SPEC)
        self._target_lang = target_lang

    def after_set(self, value: str) -> None:
        """Retag proofing language so Word does not flag the translation as misspelled.

        Only rewrites a ``w:lang`` that is already present. Inserting one would
        mean placing it correctly inside the strictly ordered ``CT_RPr`` sequence,
        and a misplaced child makes Word report the file as corrupt — not a risk
        worth taking to remove red squiggles from a run that inherits its
        language from the paragraph style.
        """
        if not self._target_lang:
            return
        for run in self.runs():
            properties = run.find(W_RPR)
            if properties is None:
                continue
            lang = properties.find(W_LANG)
            if lang is not None:
                lang.set(w("val"), self._target_lang)


class DocxHandler(FormatHandler):
    extensions = ("docx",)
    output_extension = ".docx"
    output_mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    def load(self, data: bytes) -> Any:
        from docx import Document

        try:
            return Document(io.BytesIO(data))
        except Exception as exc:
            raise DocumentFormatError(f"Could not read DOCX file: {exc}") from exc

    def save(self, document: Any) -> bytes:
        buffer = io.BytesIO()
        document.save(buffer)
        return buffer.getvalue()

    def units(self, document: Any) -> Iterator[TextUnit]:
        for element, context in self._text_parts(document):
            for paragraph in element.iter(W_P):
                for row in paragraph_rows(paragraph, DOCX_SPEC):
                    yield _DocxRow(row, context, self.target_lang)

    def _text_parts(self, document: Any) -> list[tuple[Any, str]]:
        """XML parts holding visible text, main body first and the rest name-sorted.

        Sorting keeps traversal order identical between the extract pass and the
        rebuild pass, which is what segment ids rely on. Headers and footers come
        from the package rather than ``section.header``, because that property
        creates a missing definition as a side effect and would alter the file.
        """
        parts: list[tuple[str, Any, str]] = []
        for part in document.part.package.iter_parts():
            content_type = getattr(part, "content_type", "") or ""
            if not content_type.endswith(_TEXT_PART_TYPES):
                continue
            element = getattr(part, "element", None)
            if element is None:
                continue
            name = str(part.partname)
            is_main = content_type.endswith(_MAIN_PART_TYPE)
            parts.append((name, element, "body" if is_main else name.strip("/")))

        parts.sort(key=lambda item: (not item[0].endswith("document.xml"), item[0]))
        return [(element, context) for _, element, context in parts]
