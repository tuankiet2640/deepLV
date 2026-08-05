import structlog
from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.database import get_db
from src.api.middleware.dependencies import get_current_user
from src.api.models.usage_log import UsageLog
from src.api.models.user import User
from src.api.services.language_detect import SUPPORTED_LANGUAGES

log = structlog.get_logger()
router = APIRouter(prefix="/users", tags=["users"])

MAX_AVATAR_SIZE = 2 * 1024 * 1024
ALLOWED_AVATAR_TYPES = {"image/png", "image/jpeg", "image/webp"}
ALLOWED_THEMES = {"light", "dark", "system"}


class UserProfileResponse(BaseModel):
    id: str
    email: str
    role: str
    is_admin: bool
    is_verified: bool
    display_name: str | None
    has_avatar: bool
    credits_balance: float
    created_at: str
    last_login_at: str | None
    default_source_lang: str
    default_target_lang: str
    theme_preference: str
    translation_count: int


class UpdateProfileRequest(BaseModel):
    display_name: str | None = None
    default_source_lang: str | None = None
    default_target_lang: str | None = None
    theme_preference: str | None = None


async def _build_profile_response(db: AsyncSession, user: User) -> UserProfileResponse:
    count_result = await db.execute(
        select(func.count(UsageLog.id)).where(UsageLog.user_id == user.id)
    )
    translation_count = count_result.scalar_one()

    return UserProfileResponse(
        id=str(user.id),
        email=user.email,
        role=user.role,
        is_admin=user.is_admin,
        is_verified=user.is_verified,
        display_name=user.display_name,
        has_avatar=user.avatar is not None,
        credits_balance=user.credits_balance,
        created_at=user.created_at.isoformat(),
        last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
        default_source_lang=user.default_source_lang,
        default_target_lang=user.default_target_lang,
        theme_preference=user.theme_preference,
        translation_count=translation_count,
    )


@router.get("/me", response_model=UserProfileResponse)
async def get_me(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> UserProfileResponse:
    return await _build_profile_response(db, user)


@router.patch("/me", response_model=UserProfileResponse)
async def update_me(
    req: UpdateProfileRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserProfileResponse:
    if req.display_name is not None:
        display_name = req.display_name.strip()
        if len(display_name) > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Display name must be 100 characters or fewer",
            )
        user.display_name = display_name or None

    if req.default_source_lang is not None:
        if req.default_source_lang != "auto" and req.default_source_lang not in SUPPORTED_LANGUAGES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported source language: {req.default_source_lang}",
            )
        user.default_source_lang = req.default_source_lang

    if req.default_target_lang is not None:
        if req.default_target_lang not in SUPPORTED_LANGUAGES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported target language: {req.default_target_lang}",
            )
        user.default_target_lang = req.default_target_lang

    if req.theme_preference is not None:
        if req.theme_preference not in ALLOWED_THEMES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Theme must be one of: {', '.join(sorted(ALLOWED_THEMES))}",
            )
        user.theme_preference = req.theme_preference

    await db.commit()
    log.info("profile_updated", user_id=str(user.id))
    return await _build_profile_response(db, user)


@router.post("/me/avatar", response_model=UserProfileResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserProfileResponse:
    if file.content_type not in ALLOWED_AVATAR_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported image type. Supported: {', '.join(sorted(ALLOWED_AVATAR_TYPES))}",
        )

    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File is empty")
    if len(file_bytes) > MAX_AVATAR_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Image too large. Maximum size is {MAX_AVATAR_SIZE // (1024 * 1024)}MB.",
        )

    user.avatar = file_bytes
    user.avatar_content_type = file.content_type
    await db.commit()
    log.info("avatar_uploaded", user_id=str(user.id))
    return await _build_profile_response(db, user)


@router.get("/me/avatar")
async def get_my_avatar(user: User = Depends(get_current_user)) -> Response:
    if user.avatar is None or user.avatar_content_type is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No avatar set")
    return Response(content=user.avatar, media_type=user.avatar_content_type)


@router.delete("/me/avatar", response_model=UserProfileResponse)
async def delete_avatar(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> UserProfileResponse:
    user.avatar = None
    user.avatar_content_type = None
    await db.commit()
    log.info("avatar_deleted", user_id=str(user.id))
    return await _build_profile_response(db, user)
