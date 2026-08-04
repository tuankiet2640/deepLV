"""Email OTP lifecycle: generation, hashing, verification with attempt limits."""

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.models.email_otp import EmailOTP

OTP_LENGTH = 6
OTP_EXPIRE_MINUTES = 15
MAX_OTP_ATTEMPTS = 5


def generate_otp_code() -> str:
    return "".join(secrets.choice("0123456789") for _ in range(OTP_LENGTH))


def hash_otp_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


async def create_otp(db: AsyncSession, user_id: uuid.UUID, purpose: str = "verify_email") -> str:
    """Invalidate any prior unconsumed OTPs for this (user, purpose) and issue a new one.

    Returns the raw code so the caller can email it immediately -- it is
    never persisted or returned over HTTP.
    """
    result = await db.execute(
        select(EmailOTP).where(
            EmailOTP.user_id == user_id,
            EmailOTP.purpose == purpose,
            EmailOTP.consumed.is_(False),
        )
    )
    for stale in result.scalars():
        stale.consumed = True

    code = generate_otp_code()
    otp = EmailOTP(
        user_id=user_id,
        purpose=purpose,
        code_hash=hash_otp_code(code),
        expires_at=datetime.now(UTC) + timedelta(minutes=OTP_EXPIRE_MINUTES),
    )
    db.add(otp)
    await db.commit()
    return code


async def verify_otp(
    db: AsyncSession, user_id: uuid.UUID, code: str, purpose: str = "verify_email"
) -> tuple[bool, str]:
    """Returns (ok, reason). reason is one of:
    "ok", "not_found", "expired", "locked", "invalid".
    """
    result = await db.execute(
        select(EmailOTP)
        .where(
            EmailOTP.user_id == user_id,
            EmailOTP.purpose == purpose,
            EmailOTP.consumed.is_(False),
        )
        .order_by(EmailOTP.created_at.desc())
    )
    otp = result.scalars().first()

    if otp is None:
        return False, "not_found"

    if otp.attempts >= MAX_OTP_ATTEMPTS:
        return False, "locked"

    if otp.expires_at < datetime.now(UTC):
        return False, "expired"

    if otp.code_hash != hash_otp_code(code):
        otp.attempts += 1
        await db.commit()
        return False, "invalid"

    otp.consumed = True
    await db.commit()
    return True, "ok"
