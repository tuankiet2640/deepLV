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


# Default settings and their types
DEFAULT_SETTINGS = {
    "credit_cost_per_1k_chars": "5.0",
    "max_document_size_mb": "50",
    "max_translation_chars": "10000",
    "free_tier_daily_chars": "5000",
}
