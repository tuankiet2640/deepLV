"""Splits text too long for a single provider call into translatable chunks.

Text extraction moved to ``services/document_format``, which reads documents as
addressable segments instead of one flat string. What remains here is the
fallback for a single segment that is still too big for a provider — a whole
chapter in one Word paragraph, or a cell holding an essay.
"""

import re

import structlog

log = structlog.get_logger()

# Maximum characters per chunk for translation
MAX_CHUNK_SIZE = 5000

_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")


class TextChunker:
    """Breaks long text on the most natural boundary that fits."""

    def chunk_text(self, text: str, max_chunk_size: int = MAX_CHUNK_SIZE) -> list[str]:
        """Split text into chunks a provider will accept.

        Prefers paragraph breaks, falls back to sentence breaks, and only splits
        mid-sentence when a single sentence is itself over the limit.
        """
        if len(text) <= max_chunk_size:
            return [text]

        chunks: list[str] = []
        current_chunk = ""

        for paragraph in text.split("\n\n"):
            if len(paragraph) > max_chunk_size:
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                    current_chunk = ""

                for sentence in self._split_sentences(paragraph):
                    if len(sentence) > max_chunk_size:
                        if current_chunk.strip():
                            chunks.append(current_chunk.strip())
                            current_chunk = ""
                        chunks.extend(self._hard_split(sentence, max_chunk_size))
                    elif len(current_chunk) + len(sentence) + 1 > max_chunk_size:
                        if current_chunk.strip():
                            chunks.append(current_chunk.strip())
                        current_chunk = sentence
                    else:
                        current_chunk = (
                            current_chunk + " " + sentence if current_chunk else sentence
                        )

            elif len(current_chunk) + len(paragraph) + 2 > max_chunk_size:
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                current_chunk = paragraph
            else:
                current_chunk = current_chunk + "\n\n" + paragraph if current_chunk else paragraph

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        log.info("text_chunked", total_chars=len(text), chunks=len(chunks))
        return chunks

    def _hard_split(self, text: str, max_chunk_size: int) -> list[str]:
        """Split with no regard for boundaries, for a sentence over the limit."""
        chunks = []
        for index in range(0, len(text), max_chunk_size):
            chunk = text[index : index + max_chunk_size]
            if chunk.strip():
                chunks.append(chunk.strip())
        return chunks

    def _split_sentences(self, text: str) -> list[str]:
        return [s for s in _SENTENCE_BOUNDARY.split(text) if s.strip()]
