"""Admin settings model - key-value configuration stored in DB."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from src.api.models import Base


class AdminSetting(Base):
    __tablename__ = "admin_settings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    value: Mapped[str] = mapped_column(String(500), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


# Default settings and their types.
#
# Per-provider credit rates replace a single flat credit_cost_per_1k_chars --
# each paid provider (marianmt is always free) costs the platform a
# different amount, so pricing needs to vary by provider to mean anything.
# Defaults mirror PROVIDER_INFO in provider_manager.py.
DEFAULT_SETTINGS = {
    "credit_cost_per_1k_chars_openai": "5.0",
    "credit_cost_per_1k_chars_huggingface": "2.0",
    "credit_cost_per_1k_chars_google": "3.0",
    "max_document_size_mb": "50",
    "max_translation_chars": "10000",
}
