"""Credit transaction model."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.api.models import Base


class CreditTransaction(Base):
    __tablename__ = "credit_transactions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    transaction_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # purchase, debit, refund
    description: Mapped[str] = mapped_column(String(255), nullable=False)

    # Structured fields for auditing what rate was actually charged, since
    # description is free text and the rate can change over time.
    provider: Mapped[str | None] = mapped_column(String(20), nullable=True)
    char_count: Mapped[int | None] = mapped_column(nullable=True)
    rate_applied: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_lang: Mapped[str | None] = mapped_column(String(10), nullable=True)
    target_lang: Mapped[str | None] = mapped_column(String(10), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    # Relationships
    user = relationship("User", back_populates="credit_transactions")
