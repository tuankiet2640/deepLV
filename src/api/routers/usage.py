from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.database import get_db
from src.api.middleware.dependencies import get_current_user
from src.api.models.usage_log import UsageLog
from src.api.models.user import User

router = APIRouter(prefix="/usage", tags=["usage"])


class LanguagePairStats(BaseModel):
    requests: int
    characters: int


class DailyStats(BaseModel):
    date: str
    requests: int
    characters: int


class UsageResponse(BaseModel):
    total_requests: int
    total_characters: int
    cache_hit_rate: float
    by_language_pair: dict[str, LanguagePairStats]
    daily: list[DailyStats]


class HistoryItem(BaseModel):
    id: str
    source_lang: str
    target_lang: str
    character_count: int
    cached: bool
    latency_ms: int
    provider: str | None
    created_at: str


class HistoryResponse(BaseModel):
    items: list[HistoryItem]
    total: int


@router.get("", response_model=UsageResponse)
async def get_usage(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    key_id: str | None = Query(None),
    days: int = Query(30, ge=1, le=90),
) -> UsageResponse:
    cutoff = datetime.now(UTC) - timedelta(days=days)
    base_filter = [UsageLog.user_id == user.id, UsageLog.created_at >= cutoff]
    if key_id:
        base_filter.append(UsageLog.api_key_id == key_id)

    # Totals
    totals_q = select(
        func.count().label("total_requests"),
        func.coalesce(func.sum(UsageLog.character_count), 0).label("total_characters"),
        func.coalesce(
            func.sum(case((UsageLog.cached.is_(True), 1), else_=0))
            * 1.0
            / func.nullif(func.count(), 0),
            0,
        ).label("cache_hit_rate"),
    ).where(*base_filter)
    totals_result = await db.execute(totals_q)
    totals = totals_result.one()

    # By language pair
    pair_q = (
        select(
            UsageLog.source_lang,
            UsageLog.target_lang,
            func.count().label("requests"),
            func.sum(UsageLog.character_count).label("characters"),
        )
        .where(*base_filter)
        .group_by(UsageLog.source_lang, UsageLog.target_lang)
    )
    pair_result = await db.execute(pair_q)
    by_pair = {
        f"{row.source_lang}->{row.target_lang}": LanguagePairStats(
            requests=row.requests, characters=row.characters
        )
        for row in pair_result.all()
    }

    # Daily breakdown
    daily_q = (
        select(
            func.date(UsageLog.created_at).label("day"),
            func.count().label("requests"),
            func.sum(UsageLog.character_count).label("characters"),
        )
        .where(*base_filter)
        .group_by(func.date(UsageLog.created_at))
        .order_by(func.date(UsageLog.created_at))
    )
    daily_result = await db.execute(daily_q)
    daily = [
        DailyStats(date=str(row.day), requests=row.requests, characters=row.characters)
        for row in daily_result.all()
    ]

    return UsageResponse(
        total_requests=totals.total_requests,
        total_characters=totals.total_characters,
        cache_hit_rate=round(float(totals.cache_hit_rate), 4),
        by_language_pair=by_pair,
        daily=daily,
    )


@router.get("/history", response_model=HistoryResponse)
async def get_history(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    source_lang: str | None = Query(None),
    target_lang: str | None = Query(None),
    provider: str | None = Query(None),
    days: int = Query(30, ge=1, le=90),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> HistoryResponse:
    """Get individual translation history entries with optional filtering."""
    cutoff = datetime.now(UTC) - timedelta(days=days)
    filters = [UsageLog.user_id == user.id, UsageLog.created_at >= cutoff]

    if source_lang:
        filters.append(UsageLog.source_lang == source_lang)
    if target_lang:
        filters.append(UsageLog.target_lang == target_lang)
    if provider:
        filters.append(UsageLog.provider == provider)

    # Total count
    count_q = select(func.count()).select_from(UsageLog).where(*filters)
    count_result = await db.execute(count_q)
    total = count_result.scalar_one()

    # Fetch items
    items_q = (
        select(UsageLog)
        .where(*filters)
        .order_by(UsageLog.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    items_result = await db.execute(items_q)
    items = [
        HistoryItem(
            id=str(row.id),
            source_lang=row.source_lang,
            target_lang=row.target_lang,
            character_count=row.character_count,
            cached=row.cached,
            latency_ms=row.latency_ms,
            provider=row.provider,
            created_at=row.created_at.isoformat(),
        )
        for row in items_result.scalars().all()
    ]

    return HistoryResponse(items=items, total=total)
