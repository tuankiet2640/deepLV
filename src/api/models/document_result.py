"""Document translation result model."""

import uuid

from sqlalchemy import ForeignKey, Integer, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.api.models import Base


class DocumentResult(Base):
    __tablename__ = "document_results"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_jobs.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    translated_content: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False)
    total_characters: Mapped[int] = mapped_column(Integer, nullable=False)
    # Format-preserving output, when the original format could be rebuilt
    # (docx, pdf). Null for txt originals or if rebuild failed, in which case
    # download falls back to translated_content as a plain-text file.
    translated_file_bytes: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    output_format: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Relationships
    job = relationship("DocumentJob", back_populates="result")
