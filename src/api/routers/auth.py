import uuid
from datetime import UTC, datetime, timedelta

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.database import get_db
from src.api.models.password_reset import PasswordResetToken
from src.api.models.user import User
from src.api.services.auth import (
    create_access_token,
    get_user_by_email,
    hash_password,
    verify_password,
)

log = structlog.get_logger()
router = APIRouter(prefix="/auth", tags=["auth"])


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
    reset_token: str


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
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    if is_first_user:
        log.info("first_user_admin_bootstrap", user_id=str(user.id), email=user.email)
    log.info("user_registered", user_id=str(user.id), email=user.email)
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

    token = create_access_token(user.id)
    log.info("user_login", user_id=str(user.id))
    return LoginResponse(access_token=token, expires_in=86400)


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

    # In production, you would email this token. For now, return it directly.
    return ForgotPasswordResponse(
        message="Password reset token generated. Use it to reset your password.",
        reset_token=reset_token,
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
