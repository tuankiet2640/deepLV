"""Translated document file produced by a document job."""

import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.api.models import Base


class DocumentArtifact(Base):
    """The downloadable output file, kept alongside the plain-text result.

    Held in its own table rather than as extra columns on ``document_results``
    because deployments build their schema from ``Base.metadata.create_all``,
    which creates new tables but never alters existing ones. Jobs translated
    before format preservation existed simply have no artifact row, and the
    download endpoint falls back to the plain-text result for them.
    """

    __tablename__ = "document_artifacts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_jobs.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    content: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(150), nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    # False when the output file type differs from the input (PDF becomes DOCX),
    # so the UI can tell the user their layout was rebuilt, not preserved.
    format_preserved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    segment_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    translated_segments: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_segments: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    job = relationship("DocumentJob", back_populates="artifact")
