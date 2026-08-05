import asyncio
import time

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.database import async_session, get_db
from src.api.middleware.dependencies import get_optional_user
from src.api.middleware.rate_limit import RateLimiter
from src.api.models.api_key import APIKey
from src.api.models.glossary_term import GlossaryTerm
from src.api.models.usage_log import UsageLog
from src.api.models.user import User
from src.api.services import glossary
from src.api.services.language_detect import LANGUAGE_NAMES, SUPPORTED_LANGUAGES, detect_language
from src.api.services.provider_manager import ProviderManager
from src.api.services.providers.base import ProviderError

log = structlog.get_logger()
router = APIRouter(tags=["translate"])

ANON_MAX_REQUESTS = 20
ANON_WINDOW_SECONDS = 3600


def _client_ip(request: Request) -> str:
    """Railway (and most PaaS) sit behind a proxy, so request.client.host is
    the proxy's address -- read the real client IP from X-Forwarded-For when
    present (first entry is the original client)."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


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
    auth: tuple[User | None, "APIKey | None"] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
) -> TranslateResponse:
    user, api_key = auth

    # Anonymous requests get a tight, IP-limited MarianMT-only tier -- signing
    # in unlocks the other providers and the higher per-account rate limit.
    if user is None and req.provider != "marianmt":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sign in to use providers other than MarianMT",
        )

    start = time.monotonic()

    # Rate limit check (skip if Redis unavailable)
    redis_client = request.app.state.redis
    if user is not None:
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
    elif redis_client is not None:
        anon_limiter = RateLimiter(
            redis_client, max_requests=ANON_MAX_REQUESTS, window_seconds=ANON_WINDOW_SECONDS
        )
        allowed, remaining = await anon_limiter.check(f"anon-translate:{_client_ip(request)}")
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Free translation limit reached for this hour. Sign in for a higher limit.",
                headers={"Retry-After": "3600"},
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

    # Glossary: substitute matching terms with placeholders before caching
    # or translating (see src/api/services/glossary.py for why the cache
    # key can safely use the substituted text unchanged). Anonymous users
    # have no glossary, so substituted_text == req.text for them.
    glossary_terms: list[GlossaryTerm] = []
    if user is not None:
        glossary_terms = await glossary.get_terms_for_pair(
            db, user.id, source_lang, req.target_lang
        )
    substituted_text = glossary.substitute(req.text, glossary_terms) if glossary_terms else req.text

    # Cache check
    cache = request.app.state.translation_cache
    cached_result = None
    if cache is not None:
        cached_result = await cache.get(source_lang, req.target_lang, substituted_text)
    if cached_result:
        elapsed = (time.monotonic() - start) * 1000
        final_text = (
            glossary.restore(cached_result["translated_text"], glossary_terms)
            if glossary_terms
            else cached_result["translated_text"]
        )
        response = TranslateResponse(
            translated_text=final_text,
            source_lang=source_lang,
            target_lang=req.target_lang,
            detected_lang=detected,
            cached=True,
            latency_ms=round(elapsed, 1),
            provider=req.provider,
        )
        if user is not None:
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

    # Deduct credits only when the platform's admin key was used. Only
    # authenticated users can reach a non-marianmt provider (anonymous
    # requests were rejected above), so user is guaranteed non-None here.
    if req.provider != "marianmt" and not resolved.used_own_key:
        assert user is not None
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
        translated_text = await provider.translate(substituted_text, source_lang, req.target_lang)
    except ProviderError as e:
        raise HTTPException(status_code=503, detail=str(e))

    # Cache the placeholder-templated output (never the final per-user
    # restored text) keyed on the substituted text, so a shared cache entry
    # can never leak one user's target_term to another -- each request
    # restores locally from its own glossary terms below.
    if cache is not None:
        await cache.set(
            source_lang,
            req.target_lang,
            substituted_text,
            {
                "translated_text": translated_text,
                "source_lang": source_lang,
                "target_lang": req.target_lang,
            },
        )

    final_text = (
        glossary.restore(translated_text, glossary_terms) if glossary_terms else translated_text
    )

    elapsed = (time.monotonic() - start) * 1000

    # Log usage asynchronously (anonymous requests have no user to attribute it to)
    if user is not None:
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
        translated_text=final_text,
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
