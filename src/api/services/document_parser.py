"""Document parsing service.

Extracts text content from PDF, DOCX, and TXT files,
then chunks it for translation.
"""

import io

import structlog

log = structlog.get_logger()

# Maximum characters per chunk for translation
MAX_CHUNK_SIZE = 5000

SUPPORTED_FORMATS = {"pdf", "docx", "txt"}


class DocumentParseError(Exception):
    """Raised when a document cannot be parsed."""

    pass


class DocumentParser:
    """Parses uploaded documents and extracts text content."""

    def parse(self, file_bytes: bytes, filename: str) -> str:
        """Parse a document and return its text content.

        Args:
            file_bytes: Raw bytes of the uploaded file.
            filename: Original filename (used to determine format).

        Returns:
            Extracted text content.

        Raises:
            DocumentParseError: If format is unsupported or parsing fails.
        """
        extension = self._get_extension(filename)

        if extension == "pdf":
            return self.parse_pdf(file_bytes)
        elif extension == "docx":
            return self.parse_docx(file_bytes)
        elif extension == "txt":
            return self.parse_txt(file_bytes)
        else:
            raise DocumentParseError(
                f"Unsupported file format: .{extension}. "
                f"Supported formats: {', '.join(sorted(SUPPORTED_FORMATS))}"
            )

    def parse_pdf(self, file_bytes: bytes) -> str:
        """Extract text from a PDF file.

        Args:
            file_bytes: Raw PDF bytes.

        Returns:
            Extracted text content.
        """
        try:
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(file_bytes))
            pages = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    pages.append(text)

            content = "\n\n".join(pages)
            if not content.strip():
                raise DocumentParseError(
                    "PDF appears to contain no extractable text. "
                    "Scanned PDFs without OCR are not supported."
                )
            log.info("pdf_parsed", pages=len(reader.pages), chars=len(content))
            return content
        except DocumentParseError:
            raise
        except Exception as e:
            raise DocumentParseError(f"Failed to parse PDF: {e}") from e

    def parse_docx(self, file_bytes: bytes) -> str:
        """Extract text from a DOCX file.

        Args:
            file_bytes: Raw DOCX bytes.

        Returns:
            Extracted text content.
        """
        try:
            from docx import Document

            doc = Document(io.BytesIO(file_bytes))
            paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]

            content = "\n\n".join(paragraphs)
            if not content.strip():
                raise DocumentParseError("DOCX file contains no text content.")
            log.info("docx_parsed", paragraphs=len(paragraphs), chars=len(content))
            return content
        except DocumentParseError:
            raise
        except Exception as e:
            raise DocumentParseError(f"Failed to parse DOCX: {e}") from e

    def parse_txt(self, file_bytes: bytes) -> str:
        """Extract text from a plain text file.

        Args:
            file_bytes: Raw TXT bytes.

        Returns:
            Decoded text content.
        """
        try:
            # Try UTF-8 first, fall back to latin-1
            try:
                content = file_bytes.decode("utf-8")
            except UnicodeDecodeError:
                content = file_bytes.decode("latin-1")

            if not content.strip():
                raise DocumentParseError("Text file is empty.")
            log.info("txt_parsed", chars=len(content))
            return content
        except DocumentParseError:
            raise
        except Exception as e:
            raise DocumentParseError(f"Failed to parse text file: {e}") from e

    def chunk_text(self, text: str, max_chunk_size: int = MAX_CHUNK_SIZE) -> list[str]:
        """Split text into chunks suitable for translation.

        Splits on paragraph boundaries where possible, falling back
        to sentence boundaries, then hard splits at max_chunk_size.

        Args:
            text: Full text to chunk.
            max_chunk_size: Maximum characters per chunk.

        Returns:
            List of text chunks.
        """
        if len(text) <= max_chunk_size:
            return [text]

        chunks: list[str] = []
        # Split by paragraphs first
        paragraphs = text.split("\n\n")
        current_chunk = ""

        for paragraph in paragraphs:
            # If a single paragraph exceeds max size, split it further
            if len(paragraph) > max_chunk_size:
                # Flush current chunk
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                    current_chunk = ""

                # Split long paragraph by sentences
                sentences = self._split_sentences(paragraph)
                for sentence in sentences:
                    # If a single sentence exceeds max size, hard-split it
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
                # Current chunk would exceed limit, start a new one
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                current_chunk = paragraph
            else:
                current_chunk = current_chunk + "\n\n" + paragraph if current_chunk else paragraph

        # Don't forget the last chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        log.info("text_chunked", total_chars=len(text), chunks=len(chunks))
        return chunks

    def _hard_split(self, text: str, max_chunk_size: int) -> list[str]:
        """Hard-split text into chunks of max_chunk_size when no natural boundaries exist."""
        chunks = []
        for i in range(0, len(text), max_chunk_size):
            chunk = text[i : i + max_chunk_size]
            if chunk.strip():
                chunks.append(chunk.strip())
        return chunks

    def _split_sentences(self, text: str) -> list[str]:
        """Split text into sentences (simple heuristic)."""
        import re

        sentences = re.split(r"(?<=[.!?])\s+", text)
        return [s for s in sentences if s.strip()]

    def _get_extension(self, filename: str) -> str:
        """Get lowercase file extension without dot."""
        if "." not in filename:
            return ""
        return filename.rsplit(".", 1)[-1].lower()
