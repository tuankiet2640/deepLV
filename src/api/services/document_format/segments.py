"""Translation units extracted from a document."""

import re
from dataclasses import dataclass

# A segment longer than this is sub-chunked before it reaches a provider.
MAX_SEGMENT_CHARS = 4000

_URL_RE = re.compile(r"^(https?://|www\.)\S+$", re.IGNORECASE)
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[a-z]{2,}$", re.IGNORECASE)
_PLACEHOLDER_RE = re.compile(r"^[{<%$][^\s]*[}>%s]$")


@dataclass(frozen=True)
class Segment:
    """One piece of text to translate, addressed by its position in the walk order.

    ``id`` is the index of the text unit within the handler's deterministic walk,
    which is what lets rebuild re-open the original file and put the translation
    back in the right place without carrying any parsed state around.
    """

    id: int
    text: str
    context: str = ""
    translatable: bool = True


def is_translatable(text: str) -> bool:
    """Whether a text unit is worth sending to a provider.

    Filters out units that would waste credits and that MT typically mangles:
    blank runs, bare numbers and dates, URLs, emails, and format placeholders.
    """
    stripped = text.strip()
    if not stripped:
        return False
    # Covers CJK as well — CJK codepoints are alphabetic in Python, while pure
    # numbers, dates, currency and punctuation are not.
    if not any(char.isalpha() for char in stripped):
        return False
    if _URL_RE.match(stripped) or _EMAIL_RE.match(stripped):
        return False
    if _PLACEHOLDER_RE.match(stripped):
        return False
    return True


def split_outer_whitespace(text: str) -> tuple[str, str, str]:
    """Split text into (leading whitespace, core, trailing whitespace).

    Providers strip surrounding whitespace, which matters for inline HTML nodes
    and indented text lines. The core is translated and the padding re-applied.
    """
    if not text.strip():
        return "", "", text
    lead = len(text) - len(text.lstrip())
    tail = len(text) - len(text.rstrip())
    return text[:lead], text[lead : len(text) - tail], text[len(text) - tail :]
