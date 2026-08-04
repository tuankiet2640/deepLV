"""Admin dashboard router.

Provides endpoints for admin users to manage users, view usage analytics,
manage admin provider keys, and update system settings.
"""

from datetime import UTC

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.database import get_db
from src.api.middleware.admin import get_admin_user
from src.api.models.admin_provider_key import AdminProviderKey
from src.api.models.admin_settings import DEFAULT_SETTINGS, AdminSetting
from src.api.models.usage_log import UsageLog
from src.api.models.user import User
from src.api.services.encryption import encrypt_api_key

log = structlog.get_logger()
router = APIRouter(prefix="/admin", tags=["admin"])


# --- Pydantic schemas ---


class UserSummary(BaseModel):
    id: str
    email: str
    is_admin: bool
    is_verified: bool
    display_name: str | None
    credits_balance: float
    created_at: str
    usage_count: int
    total_chars_translated: int


class UsersListResponse(BaseModel):
    users: list[UserSummary]
    total: int


class UserDetailResponse(BaseModel):
    id: str
    email: str
    is_admin: bool
    is_verified: bool
    display_name: str | None
    credits_balance: float
    created_at: str
    usage_count: int
    total_chars_translated: int
    recent_usage: list[dict]


class UpdateUserRequest(BaseModel):
    is_admin: bool | None = None
    credits_balance: float | None = None


class UpdateUserResponse(BaseModel):
    id: str
    email: str
    is_admin: bool
    credits_balance: float


class UsageAnalyticsResponse(BaseModel):
    total_translations: int
    total_characters: int
    total_users: int
    active_users_30d: int
    translations_by_provider: dict[str, int]
    translations_by_lang_pair: list[dict]
    daily_usage: list[dict]


class AdminProviderKeyResponse(BaseModel):
    id: str
    provider: str
    is_active: bool
    usage_count: int
    created_at: str


class AdminProviderKeyListResponse(BaseModel):
    keys: list[AdminProviderKeyResponse]


class CreateAdminKeyRequest(BaseModel):
    provider: str
    api_key: str


class SettingResponse(BaseModel):
    key: str
    value: str


class SettingsResponse(BaseModel):
    settings: list[SettingResponse]


class UpdateSettingsRequest(BaseModel):
    settings: dict[str, str]


# --- User Management Endpoints ---


@router.get("/users", response_model=UsersListResponse)
async def list_users(
    _admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> UsersListResponse:
    """List all users with usage statistics."""
    # Get total user count
    count_result = await db.execute(select(func.count()).select_from(User))
    total = count_result.scalar_one()

    # Build a subquery for usage stats to avoid N+1 queries
    usage_subq = (
        select(
            UsageLog.user_id,
            func.count(UsageLog.id).label("usage_count"),
            func.coalesce(func.sum(UsageLog.character_count), 0).label("total_chars"),
        )
        .group_by(UsageLog.user_id)
        .subquery()
    )

    # Join users with usage stats in a single query
    result = await db.execute(
        select(
            User,
            func.coalesce(usage_subq.c.usage_count, 0).label("usage_count"),
            func.coalesce(usage_subq.c.total_chars, 0).label("total_chars"),
        )
        .outerjoin(usage_subq, User.id == usage_subq.c.user_id)
        .order_by(User.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = result.all()

    user_summaries = [
        UserSummary(
            id=str(row.User.id),
            email=row.User.email,
            is_admin=row.User.is_admin,
            is_verified=row.User.is_verified,
            display_name=row.User.display_name,
            credits_balance=row.User.credits_balance,
            created_at=row.User.created_at.isoformat(),
            usage_count=int(row.usage_count),
            total_chars_translated=int(row.total_chars),
        )
        for row in rows
    ]

    return UsersListResponse(users=user_summaries, total=total)


@router.get("/users/{user_id}", response_model=UserDetailResponse)
async def get_user_detail(
    user_id: str,
    _admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> UserDetailResponse:
    """Get detailed information about a specific user."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Get usage stats
    stats_result = await db.execute(
        select(
            func.count(UsageLog.id).label("usage_count"),
            func.coalesce(func.sum(UsageLog.character_count), 0).label("total_chars"),
        ).where(UsageLog.user_id == user.id)
    )
    stats = stats_result.one()

    # Get recent usage logs
    recent_result = await db.execute(
        select(UsageLog)
        .where(UsageLog.user_id == user.id)
        .order_by(UsageLog.created_at.desc())
        .limit(10)
    )
    recent_logs = recent_result.scalars().all()

    return UserDetailResponse(
        id=str(user.id),
        email=user.email,
        is_admin=user.is_admin,
        is_verified=user.is_verified,
        display_name=user.display_name,
        credits_balance=user.credits_balance,
        created_at=user.created_at.isoformat(),
        usage_count=stats.usage_count,
        total_chars_translated=int(stats.total_chars),
        recent_usage=[
            {
                "id": str(log_entry.id),
                "source_lang": log_entry.source_lang,
                "target_lang": log_entry.target_lang,
                "character_count": log_entry.character_count,
                "provider": log_entry.provider or "marianmt",
                "created_at": log_entry.created_at.isoformat(),
            }
            for log_entry in recent_logs
        ],
    )


@router.patch("/users/{user_id}", response_model=UpdateUserResponse)
async def update_user(
    user_id: str,
    req: UpdateUserRequest,
    _admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> UpdateUserResponse:
    """Update a user's admin status or credits balance."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if req.is_admin is not None:
        user.is_admin = req.is_admin
    if req.credits_balance is not None:
        if req.credits_balance < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Credits balance cannot be negative",
            )
        user.credits_balance = req.credits_balance

    await db.commit()
    await db.refresh(user)

    log.info(
        "admin_user_updated",
        target_user_id=str(user.id),
        is_admin=user.is_admin,
        credits_balance=user.credits_balance,
    )
    return UpdateUserResponse(
        id=str(user.id),
        email=user.email,
        is_admin=user.is_admin,
        credits_balance=user.credits_balance,
    )


# --- Usage Analytics Endpoints ---


@router.get("/usage", response_model=UsageAnalyticsResponse)
async def get_usage_analytics(
    _admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> UsageAnalyticsResponse:
    """Get global usage analytics for the platform."""
    # Total translations and characters
    totals_result = await db.execute(
        select(
            func.count(UsageLog.id).label("total_translations"),
            func.coalesce(func.sum(UsageLog.character_count), 0).label("total_characters"),
        )
    )
    totals = totals_result.one()

    # Total users
    users_result = await db.execute(select(func.count()).select_from(User))
    total_users = users_result.scalar_one()

    # Active users in last 30 days (users with at least one usage log)
    from datetime import datetime, timedelta

    thirty_days_ago = datetime.now(UTC) - timedelta(days=30)
    active_result = await db.execute(
        select(func.count(func.distinct(UsageLog.user_id))).where(
            UsageLog.created_at >= thirty_days_ago
        )
    )
    active_users_30d = active_result.scalar_one()

    # Translations by provider
    provider_result = await db.execute(
        select(
            func.coalesce(UsageLog.provider, "marianmt").label("provider"),
            func.count(UsageLog.id).label("count"),
        ).group_by(func.coalesce(UsageLog.provider, "marianmt"))
    )
    translations_by_provider: dict[str, int] = {
        row.provider: row.count for row in provider_result.all()
    }

    # Translations by language pair (top 10)
    lang_pair_result = await db.execute(
        select(
            UsageLog.source_lang,
            UsageLog.target_lang,
            func.count(UsageLog.id).label("count"),
        )
        .group_by(UsageLog.source_lang, UsageLog.target_lang)
        .order_by(func.count(UsageLog.id).desc())
        .limit(10)
    )
    translations_by_lang_pair = [
        {
            "source_lang": row.source_lang,
            "target_lang": row.target_lang,
            "count": row.count,
        }
        for row in lang_pair_result.all()
    ]

    # Daily usage for last 30 days
    daily_result = await db.execute(
        select(
            func.date(UsageLog.created_at).label("date"),
            func.count(UsageLog.id).label("count"),
            func.coalesce(func.sum(UsageLog.character_count), 0).label("characters"),
        )
        .where(UsageLog.created_at >= thirty_days_ago)
        .group_by(func.date(UsageLog.created_at))
        .order_by(func.date(UsageLog.created_at))
    )
    daily_usage = [
        {
            "date": str(row.date),
            "translations": row.count,
            "characters": int(row.characters),
        }
        for row in daily_result.all()
    ]

    return UsageAnalyticsResponse(
        total_translations=totals.total_translations,
        total_characters=int(totals.total_characters),
        total_users=total_users,
        active_users_30d=active_users_30d,
        translations_by_provider=translations_by_provider,
        translations_by_lang_pair=translations_by_lang_pair,
        daily_usage=daily_usage,
    )


# --- Admin Provider Keys Endpoints ---


@router.get("/provider-keys", response_model=AdminProviderKeyListResponse)
async def list_admin_provider_keys(
    _admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> AdminProviderKeyListResponse:
    """List all admin provider keys."""
    result = await db.execute(select(AdminProviderKey).order_by(AdminProviderKey.created_at.desc()))
    keys = result.scalars().all()
    return AdminProviderKeyListResponse(
        keys=[
            AdminProviderKeyResponse(
                id=str(k.id),
                provider=k.provider,
                is_active=k.is_active,
                usage_count=k.usage_count,
                created_at=k.created_at.isoformat(),
            )
            for k in keys
        ]
    )


@router.post(
    "/provider-keys",
    response_model=AdminProviderKeyResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_admin_provider_key(
    req: CreateAdminKeyRequest,
    _admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> AdminProviderKeyResponse:
    """Add a new admin provider key for credit-based translations."""
    valid_providers = ["openai", "huggingface", "google", "deepl"]
    if req.provider not in valid_providers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported provider: {req.provider}. Supported: {', '.join(valid_providers)}",
        )

    admin_key = AdminProviderKey(
        provider=req.provider,
        encrypted_api_key=encrypt_api_key(req.api_key),
        is_active=True,
    )
    db.add(admin_key)
    await db.commit()
    await db.refresh(admin_key)

    log.info("admin_provider_key_created", provider=req.provider, key_id=str(admin_key.id))
    return AdminProviderKeyResponse(
        id=str(admin_key.id),
        provider=admin_key.provider,
        is_active=admin_key.is_active,
        usage_count=admin_key.usage_count,
        created_at=admin_key.created_at.isoformat(),
    )


@router.delete("/provider-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_admin_provider_key(
    key_id: str,
    _admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete an admin provider key."""
    result = await db.execute(select(AdminProviderKey).where(AdminProviderKey.id == key_id))
    key = result.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider key not found")

    await db.delete(key)
    await db.commit()
    log.info("admin_provider_key_deleted", key_id=key_id)


# --- Settings Endpoints ---


@router.get("/settings", response_model=SettingsResponse)
async def get_settings(
    _admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> SettingsResponse:
    """Get all admin settings. Returns defaults for any unset values."""
    result = await db.execute(select(AdminSetting))
    stored = {s.key: s.value for s in result.scalars().all()}

    # Merge with defaults
    all_settings = {**DEFAULT_SETTINGS, **stored}
    return SettingsResponse(
        settings=[SettingResponse(key=k, value=v) for k, v in all_settings.items()]
    )


@router.patch("/settings", response_model=SettingsResponse)
async def update_settings(
    req: UpdateSettingsRequest,
    _admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> SettingsResponse:
    """Update admin settings (credit pricing, limits, etc.)."""
    # Settings that must have valid numeric values
    numeric_settings = {
        "credit_cost_per_1k_chars",
        "max_document_size_mb",
        "max_translation_chars",
        "free_tier_daily_chars",
    }

    for key, value in req.settings.items():
        if key not in DEFAULT_SETTINGS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown setting: {key}. Valid: {', '.join(DEFAULT_SETTINGS.keys())}",
            )

        # Validate numeric settings
        if key in numeric_settings:
            try:
                numeric_val = float(value)
                if numeric_val < 0:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Setting '{key}' must be a non-negative number, got: {value}",
                    )
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Setting '{key}' must be a valid number, got: {value}",
                )

        # Upsert the setting
        result = await db.execute(select(AdminSetting).where(AdminSetting.key == key))
        existing = result.scalar_one_or_none()
        if existing:
            existing.value = value
        else:
            db.add(AdminSetting(key=key, value=value))

    await db.commit()
    log.info("admin_settings_updated", settings=req.settings)

    # Return updated settings
    result = await db.execute(select(AdminSetting))
    stored = {s.key: s.value for s in result.scalars().all()}
    all_settings = {**DEFAULT_SETTINGS, **stored}
    return SettingsResponse(
        settings=[SettingResponse(key=k, value=v) for k, v in all_settings.items()]
    )
