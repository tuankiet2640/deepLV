"""Document parsing service.

Extracts text content from PDF, DOCX, and TXT files,
then chunks it for translation.
"""

import io

import structlog

log = structlog.get_logger()

# Formats we can reconstruct as a translated file in their original format.
# Everything else (txt) falls back to a plain-text download.
REBUILDABLE_FORMATS = {"docx", "pdf"}

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
        extension = self.get_extension(filename)

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
            paragraphs = self._docx_paragraph_texts(file_bytes)
            content = "\n\n".join(paragraphs)
            if not content.strip():
                raise DocumentParseError("DOCX file contains no text content.")
            log.info("docx_parsed", paragraphs=len(paragraphs), chars=len(content))
            return content
        except DocumentParseError:
            raise
        except Exception as e:
            raise DocumentParseError(f"Failed to parse DOCX: {e}") from e

    def _docx_paragraph_texts(self, file_bytes: bytes) -> list[str]:
        """Return the non-empty paragraph texts of a DOCX, in document order.

        This exact filter (skip paragraphs whose text is blank) is also used by
        ``build_translated_docx`` when walking the document to substitute
        translated text back in, so the two must stay in lockstep: the Nth
        entry returned here must always correspond to the Nth non-empty
        paragraph encountered when re-walking ``doc.paragraphs``.
        """
        from docx import Document

        doc = Document(io.BytesIO(file_bytes))
        return [para.text for para in doc.paragraphs if para.text.strip()]

    def parse_paragraphs(self, file_bytes: bytes, filename: str) -> list[str]:
        """Parse a document into its constituent paragraphs (or pages, for PDF).

        Unlike ``parse``, which returns one flattened string, this preserves
        the paragraph boundaries needed to rebuild a translated file in its
        original format (see ``build_translated_docx``/``build_translated_pdf``).

        Args:
            file_bytes: Raw bytes of the uploaded file.
            filename: Original filename (used to determine format).

        Returns:
            Non-empty paragraph/page texts, in document order.

        Raises:
            DocumentParseError: If format is unsupported or parsing fails.
        """
        extension = self.get_extension(filename)

        if extension == "docx":
            paragraphs = self._docx_paragraph_texts(file_bytes)
            if not paragraphs:
                raise DocumentParseError("DOCX file contains no text content.")
            return paragraphs
        elif extension == "pdf":
            content = self.parse_pdf(file_bytes)
            return [p for p in content.split("\n\n") if p.strip()]
        elif extension == "txt":
            content = self.parse_txt(file_bytes)
            paragraphs = [p for p in content.split("\n\n") if p.strip()]
            return paragraphs or [content]
        else:
            raise DocumentParseError(
                f"Unsupported file format: .{extension}. "
                f"Supported formats: {', '.join(sorted(SUPPORTED_FORMATS))}"
            )

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

    def build_translated_docx(
        self, original_file_bytes: bytes, translated_paragraphs: list[str]
    ) -> bytes:
        """Rebuild a DOCX with paragraph text replaced by its translation.

        Reopens the original document and walks its paragraphs in the same
        order/filter as ``_docx_paragraph_texts``, substituting each non-empty
        paragraph's text with the corresponding translated entry. This keeps
        the original styles, headers/footers, and non-text paragraphs intact;
        only body paragraph text changes.

        Args:
            original_file_bytes: The originally uploaded DOCX bytes.
            translated_paragraphs: Translated text, one entry per non-empty
                paragraph, in the same order ``_docx_paragraph_texts`` returns.

        Returns:
            Bytes of the rebuilt DOCX file.
        """
        from docx import Document

        doc = Document(io.BytesIO(original_file_bytes))
        index = 0
        for para in doc.paragraphs:
            if not para.text.strip():
                continue
            if index < len(translated_paragraphs):
                self._set_paragraph_text(para, translated_paragraphs[index])
            index += 1

        out = io.BytesIO()
        doc.save(out)
        return out.getvalue()

    def _set_paragraph_text(self, paragraph: object, new_text: str) -> None:
        """Replace a paragraph's visible text while preserving its formatting.

        Keeps the first run (and its font/bold/italic/etc.) and empties any
        remaining runs, rather than rebuilding runs from scratch, so
        character-level formatting on the paragraph's dominant run survives.
        """
        runs = paragraph.runs
        if not runs:
            paragraph.add_run(new_text)
            return
        runs[0].text = new_text
        for run in runs[1:]:
            run.text = ""

    def build_translated_pdf(self, translated_paragraphs: list[str]) -> bytes:
        """Render translated paragraphs as a new, simply-flowed PDF.

        PDFs don't expose an editable text layer the way DOCX does, so exact
        layout (fonts, positions, images) can't be preserved. Instead this
        generates a fresh, readable PDF containing all translated text,
        flowed paragraph by paragraph rather than dumping it as a .txt file.

        Args:
            translated_paragraphs: Translated paragraph/page texts, in order.

        Returns:
            Bytes of the generated PDF file.
        """
        from xml.sax.saxutils import escape

        from reportlab.lib.pagesizes import LETTER
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=LETTER,
            leftMargin=inch,
            rightMargin=inch,
            topMargin=inch,
            bottomMargin=inch,
        )
        styles = getSampleStyleSheet()
        body_style = styles["BodyText"]

        flowables = []
        for paragraph_text in translated_paragraphs:
            # Reportlab's Paragraph interprets its text as a small XML dialect;
            # escape it so literal &, <, > in translated text don't break rendering.
            safe_text = escape(paragraph_text).replace("\n", "<br/>")
            flowables.append(Paragraph(safe_text, body_style))
            flowables.append(Spacer(1, 12))

        doc.build(flowables)
        return buffer.getvalue()

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

    def get_extension(self, filename: str) -> str:
        """Get lowercase file extension without dot."""
        if "." not in filename:
            return ""
        return filename.rsplit(".", 1)[-1].lower()
