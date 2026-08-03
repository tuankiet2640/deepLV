"""Plain text handler.

Translates line by line so blank lines, indentation and the file's original line
endings all survive. Line-level units keep the output aligned with the input,
which is what makes a translated config file, subtitle list or log still usable.
"""

from collections.abc import Iterator
from typing import Any

from src.api.services.document_format.base import DocumentFormatError, FormatHandler, TextUnit
from src.api.services.document_format.segments import split_outer_whitespace


class _TextFile:
    def __init__(self, lines: list[str], newline: str, encoding: str) -> None:
        self.lines = lines
        self.newline = newline
        self.encoding = encoding


class _LineUnit:
    def __init__(self, document: _TextFile, index: int) -> None:
        self._document = document
        self._index = index

    @property
    def context(self) -> str:
        return f"line {self._index + 1}"

    def get_text(self) -> str:
        return split_outer_whitespace(self._document.lines[self._index])[1]

    def set_text(self, value: str) -> None:
        lead, _, trail = split_outer_whitespace(self._document.lines[self._index])
        self._document.lines[self._index] = f"{lead}{value}{trail}"


class TxtHandler(FormatHandler):
    extensions = ("txt",)
    output_extension = ".txt"
    output_mime = "text/plain; charset=utf-8"

    def load(self, data: bytes) -> Any:
        try:
            text = data.decode("utf-8")
            encoding = "utf-8"
        except UnicodeDecodeError:
            try:
                text = data.decode("latin-1")
                encoding = "latin-1"
            except UnicodeDecodeError as exc:
                raise DocumentFormatError(f"Could not decode text file: {exc}") from exc

        newline = "\r\n" if "\r\n" in text else "\n"
        return _TextFile(text.replace("\r\n", "\n").split("\n"), newline, encoding)

    def save(self, document: Any) -> bytes:
        joined = document.newline.join(document.lines)
        # Round-trip through the source encoding, falling back to UTF-8 when the
        # translation uses characters the original encoding cannot represent.
        try:
            return joined.encode(document.encoding)
        except UnicodeEncodeError:
            return joined.encode("utf-8")

    def units(self, document: Any) -> Iterator[TextUnit]:
        for index, line in enumerate(document.lines):
            if line.strip():
                yield _LineUnit(document, index)
