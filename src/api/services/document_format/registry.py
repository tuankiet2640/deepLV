"""Maps a filename to the handler that knows its format."""

from src.api.services.document_format.base import DocumentFormatError, FormatHandler
from src.api.services.document_format.docx_handler import DocxHandler
from src.api.services.document_format.html_handler import HtmlHandler
from src.api.services.document_format.pdf_handler import PdfHandler
from src.api.services.document_format.pptx_handler import PptxHandler
from src.api.services.document_format.txt_handler import TxtHandler
from src.api.services.document_format.xlsx_handler import XlsxHandler

HANDLER_CLASSES: tuple[type[FormatHandler], ...] = (
    DocxHandler,
    PptxHandler,
    XlsxHandler,
    PdfHandler,
    HtmlHandler,
    TxtHandler,
)

HANDLERS_BY_EXTENSION: dict[str, type[FormatHandler]] = {
    extension: handler for handler in HANDLER_CLASSES for extension in handler.extensions
}

SUPPORTED_FORMATS = frozenset(HANDLERS_BY_EXTENSION)


def file_extension(filename: str) -> str:
    """Lowercase extension without the dot."""
    if "." not in filename:
        return ""
    return filename.rsplit(".", 1)[-1].lower()


def get_handler(filename: str, target_lang: str = "") -> FormatHandler:
    """Build the handler for a filename's format.

    Raises:
        DocumentFormatError: If the extension has no handler.
    """
    extension = file_extension(filename)
    handler_class = HANDLERS_BY_EXTENSION.get(extension)
    if handler_class is None:
        supported = ", ".join(sorted(SUPPORTED_FORMATS))
        raise DocumentFormatError(
            f"Unsupported file format: .{extension}. Supported formats: {supported}"
        )
    return handler_class(target_lang=target_lang)


def format_notes() -> dict[str, str]:
    """Per-format caveats worth showing a user before they upload."""
    return {
        "pdf": (
            "PDF is translated into a DOCX file. Text and page breaks are kept; "
            "the original page layout is rebuilt rather than preserved."
        ),
        "xlsx": (
            "Cell text, styles and formulas are preserved. Charts and pivot tables "
            "are rewritten by the spreadsheet library and may lose some settings."
        ),
        "pptx": (
            "Slide text, tables and speaker notes are translated in place. "
            "Chart category labels stay in the source language."
        ),
    }


__all__ = [
    "DocumentFormatError",
    "FormatHandler",
    "HANDLERS_BY_EXTENSION",
    "SUPPORTED_FORMATS",
    "file_extension",
    "format_notes",
    "get_handler",
]
