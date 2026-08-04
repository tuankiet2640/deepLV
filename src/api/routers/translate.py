import asyncio
import time

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.database import async_session, get_db
from src.api.middleware.dependencies import get_user_from_api_key_or_jwt
from src.api.models.api_key import APIKey
from src.api.models.usage_log import UsageLog
from src.api.models.user import User
from src.api.services.language_detect import LANGUAGE_NAMES, SUPPORTED_LANGUAGES, detect_language
from src.api.services.provider_manager import ProviderManager
from src.api.services.providers.base import ProviderError

log = structlog.get_logger()
router = APIRouter(tags=["translate"])


class TranslateRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    source_lang: str = Field(..., pattern=r"^(auto|[a-z]{2})$")
    target_lang: str = Field(..., pattern=r"^[a-z]{2}$")
    provider: str = Field(default="marianmt", pattern=r"^(marianmt|openai|huggingface|google)$")
    provider_key_id: str | None = Field(default=None)


class TranslateResponse(BaseModel):
    translated_text: str
    source_lang: str
    target_lang: str
    detected_lang: bool
    cached: bool
    latency_ms: float
    provider: str = "marianmt"


class LanguageInfo(BaseModel):
    code: str
    name: str


class LanguagesResponse(BaseModel):
    languages: list[LanguageInfo]


@router.post("/translate", response_model=TranslateResponse)
async def translate(
    req: TranslateRequest,
    request: Request,
    auth: tuple[User, "APIKey | None"] = Depends(get_user_from_api_key_or_jwt),
    db: AsyncSession = Depends(get_db),
) -> TranslateResponse:
    user, api_key = auth
    start = time.monotonic()

    # Rate limit check (skip if Redis unavailable)
    rate_limiter = request.app.state.rate_limiter
    if rate_limiter is not None:
        rate_key = str(api_key.id) if api_key else str(user.id)
        allowed, remaining = await rate_limiter.check(rate_key)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers={"Retry-After": "60"},
            )

    # Language detection
    detected = False
    source_lang = req.source_lang
    if source_lang == "auto":
        source_lang = detect_language(req.text)
        detected = True

    if source_lang not in SUPPORTED_LANGUAGES:
        raise HTTPException(status_code=400, detail=f"Unsupported source language: {source_lang}")
    if req.target_lang not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported target language: {req.target_lang}",
        )
    if source_lang == req.target_lang:
        elapsed = (time.monotonic() - start) * 1000
        return TranslateResponse(
            translated_text=req.text,
            source_lang=source_lang,
            target_lang=req.target_lang,
            detected_lang=detected,
            cached=False,
            latency_ms=round(elapsed, 1),
            provider=req.provider,
        )

    # Cache check
    cache = request.app.state.translation_cache
    cached_result = None
    if cache is not None:
        cached_result = await cache.get(source_lang, req.target_lang, req.text)
    if cached_result:
        elapsed = (time.monotonic() - start) * 1000
        response = TranslateResponse(
            translated_text=cached_result["translated_text"],
            source_lang=source_lang,
            target_lang=req.target_lang,
            detected_lang=detected,
            cached=True,
            latency_ms=round(elapsed, 1),
            provider=req.provider,
        )
        asyncio.create_task(
            _log_usage(
                user.id,
                api_key.id if api_key else None,
                source_lang,
                req.target_lang,
                len(req.text),
                True,
                round(elapsed, 1),
                req.provider,
            )
        )
        return response

    # Route through ProviderManager
    settings = request.app.state.settings
    provider_manager = ProviderManager(settings)

    try:
        resolved = await provider_manager.resolve(
            provider_name=req.provider,
            user=user,
            db=db,
            provider_key_id=req.provider_key_id,
        )
    except ProviderError as e:
        raise HTTPException(status_code=400, detail=str(e))

    provider = resolved.provider

    # Deduct credits only when the platform's admin key was used
    if req.provider != "marianmt" and not resolved.used_own_key:
        has_credits = await provider_manager.deduct_credits(
            user=user, db=db, provider_name=req.provider, char_count=len(req.text)
        )
        if not has_credits:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Insufficient credits. Purchase credits or use your own API key.",
            )

    # Translate using the resolved provider
    try:
        translated_text = await provider.translate(req.text, source_lang, req.target_lang)
    except ProviderError as e:
        raise HTTPException(status_code=503, detail=str(e))

    # Cache the result
    if cache is not None:
        await cache.set(
            source_lang,
            req.target_lang,
            req.text,
            {
                "translated_text": translated_text,
                "source_lang": source_lang,
                "target_lang": req.target_lang,
            },
        )

    elapsed = (time.monotonic() - start) * 1000

    # Log usage asynchronously
    asyncio.create_task(
        _log_usage(
            user.id,
            api_key.id if api_key else None,
            source_lang,
            req.target_lang,
            len(req.text),
            False,
            round(elapsed, 1),
            req.provider,
        )
    )

    return TranslateResponse(
        translated_text=translated_text,
        source_lang=source_lang,
        target_lang=req.target_lang,
        detected_lang=detected,
        cached=False,
        latency_ms=round(elapsed, 1),
        provider=req.provider,
    )


@router.get("/languages", response_model=LanguagesResponse)
async def languages() -> LanguagesResponse:
    return LanguagesResponse(
        languages=[
            LanguageInfo(code=code, name=name) for code, name in sorted(LANGUAGE_NAMES.items())
        ]
    )


async def _log_usage(
    user_id: object,
    api_key_id: object,
    source_lang: str,
    target_lang: str,
    char_count: int,
    cached: bool,
    latency_ms: float,
    provider: str = "marianmt",
) -> None:
    """Log usage in its own DB session.

    Runs as a detached asyncio.create_task, outside the request's lifecycle,
    so it can't share the request-scoped `db` session from Depends(get_db):
    that session may already have an implicit transaction open from earlier
    work in the same request (making db.begin() here raise "a transaction is
    already begun"), and FastAPI closes it as soon as the request returns,
    possibly while this task is still running. A fresh session sidesteps
    both problems -- same pattern documents.py's background task already uses.
    """
    try:
        async with async_session() as db, db.begin():
            usage = UsageLog(
                user_id=user_id,
                api_key_id=api_key_id,
                source_lang=source_lang,
                target_lang=target_lang,
                character_count=char_count,
                cached=cached,
                latency_ms=int(latency_ms),
                provider=provider,
            )
            db.add(usage)
    except Exception:
        log.warning("usage_log_failed", exc_info=True)
