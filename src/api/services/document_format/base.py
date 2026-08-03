"""Format handler contract.

Every handler exposes one deterministic walk over the document's text units.
``extract`` reads through it, ``rebuild`` re-opens the untouched original bytes,
walks it again in the same order, and writes translations in place. Because both
phases share the same traversal, segment ids line up without persisting any
parsed state between them, and the output file is the input file with different
text — not a regenerated approximation.
"""

from abc import ABC, abstractmethod
from collections.abc import Iterator
from typing import Any, Protocol

from src.api.services.document_format.segments import Segment, is_translatable


class DocumentFormatError(Exception):
    """Raised when a document cannot be read or written."""


class TextUnit(Protocol):
    """One addressable piece of text inside a document."""

    @property
    def context(self) -> str:
        """Human-readable location, e.g. ``table`` or ``Sheet1!B4``."""
        ...

    def get_text(self) -> str: ...

    def set_text(self, value: str) -> None: ...


class FormatHandler(ABC):
    """Extracts and re-injects text for one file format."""

    extensions: tuple[str, ...] = ()
    output_extension: str = ""
    output_mime: str = "application/octet-stream"
    # False when the output file type differs from the input, so callers can tell
    # the user their layout is approximated rather than preserved.
    preserves_format: bool = True

    def __init__(self, target_lang: str = "") -> None:
        # Handlers that can record the document's language (DOCX run properties,
        # the HTML lang attribute) use this so the output is not flagged as
        # misspelled source-language text by the consuming application.
        self.target_lang = target_lang

    @abstractmethod
    def load(self, data: bytes) -> Any:
        """Parse raw bytes into the format's object model."""

    @abstractmethod
    def units(self, document: Any) -> Iterator[TextUnit]:
        """Yield every text unit in a stable, repeatable order."""

    @abstractmethod
    def save(self, document: Any) -> bytes:
        """Serialise the object model back to bytes."""

    def extract(self, data: bytes) -> list[Segment]:
        """Read every text unit out of the document."""
        document = self.load(data)
        return [
            Segment(
                id=index,
                text=unit.get_text(),
                context=unit.context,
                translatable=is_translatable(unit.get_text()),
            )
            for index, unit in enumerate(self.units(document))
        ]

    def rebuild(self, data: bytes, translations: dict[int, str]) -> bytes:
        """Write translations into a fresh copy of the original document."""
        document = self.load(data)
        for index, unit in enumerate(self.units(document)):
            replacement = translations.get(index)
            if replacement is not None:
                unit.set_text(replacement)
        return self.save(document)

    def output_filename(self, original_filename: str) -> str:
        """Name the translated file, mirroring DeepL's ``name-LANG.ext``."""
        if "." in original_filename:
            stem = original_filename.rsplit(".", 1)[0]
        else:
            stem = original_filename
        suffix = f"-{self.target_lang}" if self.target_lang else "-translated"
        return f"{stem}{suffix}{self.output_extension}"
