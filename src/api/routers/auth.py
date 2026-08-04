import uuid
from datetime import UTC, datetime, timedelta

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.database import get_db
from src.api.middleware.dependencies import get_current_user
from src.api.middleware.rate_limit import RateLimiter
from src.api.models.password_reset import PasswordResetToken
from src.api.models.user import User
from src.api.services import email, otp
from src.api.services.auth import (
    create_access_token,
    get_user_by_email,
    hash_password,
    verify_password,
)
from src.shared.config import APISettings

log = structlog.get_logger()
router = APIRouter(prefix="/auth", tags=["auth"])
settings = APISettings()


async def _check_rate_limit(
    request: Request, key: str, max_requests: int, window_seconds: int
) -> None:
    """Ad hoc rate limit for auth endpoints tighter than the global /translate limiter."""
    redis_client = request.app.state.redis
    if redis_client is None:
        return
    limiter = RateLimiter(redis_client, max_requests=max_requests, window_seconds=window_seconds)
    allowed, _ = await limiter.check(key)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later.",
        )


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterResponse(BaseModel):
    id: str
    email: str
    created_at: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    message: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class ResetPasswordResponse(BaseModel):
    message: str


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)) -> RegisterResponse:
    existing = await get_user_by_email(db, req.email)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    if len(req.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters",
        )

    # Auto-bootstrap: first registered user becomes admin
    from sqlalchemy import func
    from sqlalchemy import select as sa_select

    user_count_result = await db.execute(sa_select(func.count()).select_from(User))
    user_count = user_count_result.scalar_one()
    is_first_user = user_count == 0

    user = User(
        email=req.email,
        password_hash=hash_password(req.password),
        is_admin=is_first_user,
        is_verified=False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    if is_first_user:
        log.info("first_user_admin_bootstrap", user_id=str(user.id), email=user.email)
    log.info("user_registered", user_id=str(user.id), email=user.email)

    code = await otp.create_otp(db, user.id)
    sent = await email.send_verification_email(user.email, code)
    if not sent:
        log.warning("verification_email_not_sent", user_id=str(user.id))

    return RegisterResponse(
        id=str(user.id),
        email=user.email,
        created_at=user.created_at.isoformat(),
    )


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)) -> LoginResponse:
    user = await get_user_by_email(db, req.email)
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "email_not_verified",
                "message": "Please verify your email before logging in.",
            },
        )

    user.last_login_at = datetime.now(UTC)
    await db.commit()

    token = create_access_token(user.id)
    log.info("user_login", user_id=str(user.id))
    return LoginResponse(access_token=token, expires_in=86400)


class VerifyEmailRequest(BaseModel):
    email: EmailStr
    code: str


class ResendVerificationRequest(BaseModel):
    email: EmailStr


_OTP_REASON_MESSAGES = {
    "not_found": "No pending verification code for this account. Request a new one.",
    "expired": "This code has expired. Request a new one.",
    "locked": "Too many incorrect attempts. Request a new code.",
    "invalid": "Incorrect code.",
}


@router.post("/verify-email", response_model=LoginResponse)
async def verify_email(
    req: VerifyEmailRequest, request: Request, db: AsyncSession = Depends(get_db)
) -> LoginResponse:
    await _check_rate_limit(
        request, f"otp-verify:{req.email.lower()}", max_requests=8, window_seconds=600
    )

    user = await get_user_by_email(db, req.email)
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid code")

    if user.is_verified:
        token = create_access_token(user.id)
        return LoginResponse(access_token=token, expires_in=86400)

    ok, reason = await otp.verify_otp(db, user.id, req.code)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_OTP_REASON_MESSAGES.get(reason, "Invalid code"),
        )

    user.is_verified = True
    user.last_login_at = datetime.now(UTC)
    await db.commit()

    log.info("email_verified", user_id=str(user.id))
    token = create_access_token(user.id)
    return LoginResponse(access_token=token, expires_in=86400)


@router.post("/resend-verification")
async def resend_verification(
    req: ResendVerificationRequest, request: Request, db: AsyncSession = Depends(get_db)
) -> dict[str, str]:
    await _check_rate_limit(
        request, f"otp-resend:{req.email.lower()}", max_requests=3, window_seconds=600
    )

    user = await get_user_by_email(db, req.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No account found with that email"
        )

    if user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already verified"
        )

    code = await otp.create_otp(db, user.id)
    sent = await email.send_verification_email(user.email, code)
    if not sent:
        log.warning("verification_email_not_sent", user_id=str(user.id))

    return {"message": "Verification code sent."}


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(
    req: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)
) -> ForgotPasswordResponse:
    user = await get_user_by_email(db, req.email)
    if not user:
        # Return a generic message to avoid email enumeration
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No account found with that email",
        )

    # Generate a reset token
    reset_token = str(uuid.uuid4())
    expires_at = datetime.now(UTC) + timedelta(hours=1)

    token_record = PasswordResetToken(
        user_id=user.id,
        token=reset_token,
        expires_at=expires_at,
    )
    db.add(token_record)
    await db.commit()

    log.info("password_reset_requested", user_id=str(user.id), email=user.email)

    reset_link = f"{settings.frontend_url}/reset-password?token={reset_token}"
    sent = await email.send_password_reset_email(user.email, reset_link)
    if not sent:
        log.warning("password_reset_email_not_sent", user_id=str(user.id))

    return ForgotPasswordResponse(
        message="If an account exists for that email, a password reset link has been sent."
    )


@router.post("/reset-password", response_model=ResetPasswordResponse)
async def reset_password(
    req: ResetPasswordRequest, db: AsyncSession = Depends(get_db)
) -> ResetPasswordResponse:
    if len(req.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters",
        )

    # Find the token
    result = await db.execute(
        select(PasswordResetToken).where(PasswordResetToken.token == req.token)
    )
    token_record = result.scalar_one_or_none()

    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset token",
        )

    if token_record.used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has already been used",
        )

    if token_record.expires_at < datetime.now(UTC):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has expired",
        )

    # Update the user's password
    user_result = await db.execute(select(User).where(User.id == token_record.user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found",
        )

    user.password_hash = hash_password(req.new_password)
    token_record.used = True
    await db.commit()

    log.info("password_reset_completed", user_id=str(user.id))
    return ResetPasswordResponse(message="Password has been reset successfully")


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class ChangePasswordResponse(BaseModel):
    message: str


@router.post("/change-password", response_model=ChangePasswordResponse)
async def change_password(
    req: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChangePasswordResponse:
    if not verify_password(req.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    if len(req.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 8 characters",
        )

    current_user.password_hash = hash_password(req.new_password)
    await db.commit()

    log.info("password_changed", user_id=str(current_user.id))
    return ChangePasswordResponse(message="Password changed successfully")
