"""HTML handler.

Only text nodes and a short list of user-visible attributes are replaced, so
tags, attributes, inline styles, scripts and structure are byte-stable apart from
the translated strings. Whitespace around a text node is preserved separately
from its content, which matters for inline elements where a stripped space would
weld two words together.
"""

import io
from collections.abc import Iterator
from typing import Any

from src.api.services.document_format.base import (
    DocumentFormatError,
    FormatHandler,
    TextUnit,
)
from src.api.services.document_format.segments import split_outer_whitespace

# Their content is code or data, not prose.
SKIP_ELEMENTS = frozenset({"script", "style", "code", "pre", "kbd", "samp", "var"})
# Attributes that a reader actually sees.
TRANSLATED_ATTRS = ("alt", "title", "placeholder", "aria-label", "aria-placeholder")


class _TextNodeUnit:
    """Either an element's own text or the tail text that follows it."""

    def __init__(self, element: Any, is_tail: bool, context: str) -> None:
        self._element = element
        self._is_tail = is_tail
        self._context = context

    @property
    def context(self) -> str:
        return self._context

    def _raw(self) -> str:
        value = self._element.tail if self._is_tail else self._element.text
        return value or ""

    def get_text(self) -> str:
        return split_outer_whitespace(self._raw())[1]

    def set_text(self, value: str) -> None:
        lead, _, trail = split_outer_whitespace(self._raw())
        combined = f"{lead}{value}{trail}"
        if self._is_tail:
            self._element.tail = combined
        else:
            self._element.text = combined


class _AttrUnit:
    def __init__(self, element: Any, name: str, context: str) -> None:
        self._element = element
        self._name = name
        self._context = context

    @property
    def context(self) -> str:
        return self._context

    def get_text(self) -> str:
        return self._element.get(self._name) or ""

    def set_text(self, value: str) -> None:
        self._element.set(self._name, value)


class HtmlHandler(FormatHandler):
    extensions = ("html", "htm")
    output_extension = ".html"
    output_mime = "text/html; charset=utf-8"

    def load(self, data: bytes) -> Any:
        from lxml import html as lxml_html

        try:
            # Parsing from bytes lets lxml honour a meta charset declaration
            # instead of guessing from a pre-decoded string.
            tree = lxml_html.parse(io.BytesIO(data))
        except Exception as exc:
            raise DocumentFormatError(f"Could not read HTML file: {exc}") from exc
        if tree.getroot() is None:
            raise DocumentFormatError("HTML file contains no parsable markup.")
        return tree

    def save(self, document: Any) -> bytes:
        from lxml import html as lxml_html

        root = document.getroot()
        if self.target_lang and root.tag == "html":
            root.set("lang", self.target_lang)
        return lxml_html.tostring(
            document,
            encoding="utf-8",
            doctype=document.docinfo.doctype or None,
        )

    def units(self, document: Any) -> Iterator[TextUnit]:
        root = document.getroot()
        for element in root.iter():
            if not isinstance(element.tag, str):
                # Comments and processing instructions.
                continue

            tag = element.tag.lower()
            if tag not in SKIP_ELEMENTS:
                if (element.text or "").strip():
                    yield _TextNodeUnit(element, False, tag)
                for name in TRANSLATED_ATTRS:
                    if (element.get(name) or "").strip():
                        yield _AttrUnit(element, name, f"{tag}[{name}]")

            # A tail belongs to the parent's flow, so it is translated even when
            # the element itself is skipped: the text after </script> is prose.
            if (element.tail or "").strip():
                yield _TextNodeUnit(element, True, f"{tag}+tail")
