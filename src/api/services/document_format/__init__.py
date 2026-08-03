"""Format-preserving document translation.

Each handler extracts the text of a document as addressable segments and writes
translations back into the original file's own object model, so styling, images,
layout and metadata are carried over untouched rather than reconstructed.
"""

from src.api.services.document_format.base import DocumentFormatError, FormatHandler
from src.api.services.document_format.registry import (
    HANDLERS_BY_EXTENSION,
    SUPPORTED_FORMATS,
    file_extension,
    format_notes,
    get_handler,
)
from src.api.services.document_format.segments import (
    MAX_SEGMENT_CHARS,
    Segment,
    is_translatable,
)

__all__ = [
    "DocumentFormatError",
    "FormatHandler",
    "HANDLERS_BY_EXTENSION",
    "MAX_SEGMENT_CHARS",
    "SUPPORTED_FORMATS",
    "Segment",
    "file_extension",
    "format_notes",
    "get_handler",
    "is_translatable",
]
