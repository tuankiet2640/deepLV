"""User model."""

import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, LargeBinary, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.api.models import Base


class UserRole(enum.StrEnum):
    USER = "user"
    SUPPORT = "support"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        String(20),
        default=UserRole.USER.value,
        server_default=UserRole.USER.value,
        nullable=False,
    )
    credits_balance: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    # Email verification. server_default backfills existing rows as verified
    # on migration; register() explicitly sets is_verified=False for new signups.
    is_verified: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("true"), nullable=False
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Profile
    display_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    avatar: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    avatar_content_type: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Preferences
    default_source_lang: Mapped[str] = mapped_column(
        String(10), default="auto", server_default="auto", nullable=False
    )
    default_target_lang: Mapped[str] = mapped_column(
        String(10), default="de", server_default="de", nullable=False
    )
    theme_preference: Mapped[str] = mapped_column(
        String(10), default="system", server_default="system", nullable=False
    )

    # Relationships
    api_keys = relationship("APIKey", back_populates="user", lazy="selectin")
    provider_keys = relationship("ProviderKey", back_populates="user", lazy="selectin")
    credit_transactions = relationship("CreditTransaction", back_populates="user", lazy="selectin")
    glossary_terms = relationship("GlossaryTerm", back_populates="user", lazy="selectin")

    @property
    def is_admin(self) -> bool:
        """Back-compat shim: True iff role is admin. Superseded by `role`."""
        return self.role == UserRole.ADMIN.value

    @is_admin.setter
    def is_admin(self, value: bool) -> None:
        self.role = UserRole.ADMIN.value if value else UserRole.USER.value
