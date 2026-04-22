import asyncio
import time

import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.database import get_db
from src.api.middleware.dependencies import get_user_from_api_key
from src.api.models.api_key import APIKey
from src.api.models.usage_log import UsageLog
from src.api.models.user import User
from src.api.services.language_detect import LANGUAGE_NAMES, SUPPORTED_LANGUAGES, detect_language

log = structlog.get_logger()
router = APIRouter(tags=["translate"])


class TranslateRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    source_lang: str = Field(..., pattern=r"^(auto|[a-z]{2})$")
    target_lang: str = Field(..., pattern=r"^[a-z]{2}$")


class TranslateResponse(BaseModel):
    translated_text: str
    source_lang: str
    target_lang: str
    detected_lang: bool
    cached: bool
    latency_ms: float


class LanguageInfo(BaseModel):
    code: str
    name: str


class LanguagesResponse(BaseModel):
    languages: list[LanguageInfo]


@router.post("/translate", response_model=TranslateResponse)
async def translate(
    req: TranslateRequest,
    request: Request,
    auth: tuple[User, APIKey] = Depends(get_user_from_api_key),
    db: AsyncSession = Depends(get_db),
) -> TranslateResponse:
    user, api_key = auth
    start = time.monotonic()

    # Rate limit check
    rate_limiter = request.app.state.rate_limiter
    allowed, remaining = await rate_limiter.check(str(api_key.id))
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
        raise HTTPException(status_code=400, detail=f"Unsupported target language: {req.target_lang}")
    if source_lang == req.target_lang:
        elapsed = (time.monotonic() - start) * 1000
        return TranslateResponse(
            translated_text=req.text,
            source_lang=source_lang,
            target_lang=req.target_lang,
            detected_lang=detected,
            cached=False,
            latency_ms=round(elapsed, 1),
        )

    # Cache check
    cache = request.app.state.translation_cache
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
        )
        asyncio.create_task(_log_usage(
            db, user.id, api_key.id, source_lang, req.target_lang,
            len(req.text), True, round(elapsed, 1),
        ))
        return response

    # Forward to model worker
    worker_url = request.app.state.settings.model_worker_url
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{worker_url}/translate",
                json={
                    "text": req.text,
                    "source_lang": source_lang,
                    "target_lang": req.target_lang,
                },
            )
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Translation service unavailable")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Translation timed out")

    if resp.status_code != 200:
        log.error("worker_error", status=resp.status_code, body=resp.text)
        raise HTTPException(status_code=503, detail="Translation failed")

    worker_result = resp.json()
    translated_text = worker_result["translated_text"]

    # Cache the result
    await cache.set(source_lang, req.target_lang, req.text, {
        "translated_text": translated_text,
        "source_lang": source_lang,
        "target_lang": req.target_lang,
    })

    elapsed = (time.monotonic() - start) * 1000

    # Log usage asynchronously
    asyncio.create_task(_log_usage(
        db, user.id, api_key.id, source_lang, req.target_lang,
        len(req.text), False, round(elapsed, 1),
    ))

    return TranslateResponse(
        translated_text=translated_text,
        source_lang=source_lang,
        target_lang=req.target_lang,
        detected_lang=detected,
        cached=False,
        latency_ms=round(elapsed, 1),
    )


@router.get("/languages", response_model=LanguagesResponse)
async def languages() -> LanguagesResponse:
    return LanguagesResponse(
        languages=[
            LanguageInfo(code=code, name=name) for code, name in sorted(LANGUAGE_NAMES.items())
        ]
    )


async def _log_usage(
    db: AsyncSession,
    user_id: object,
    api_key_id: object,
    source_lang: str,
    target_lang: str,
    char_count: int,
    cached: bool,
    latency_ms: float,
) -> None:
    try:
        async with db.begin():
            usage = UsageLog(
                user_id=user_id,
                api_key_id=api_key_id,
                source_lang=source_lang,
                target_lang=target_lang,
                character_count=char_count,
                cached=cached,
                latency_ms=int(latency_ms),
            )
            db.add(usage)
    except Exception:
        log.warning("usage_log_failed", exc_info=True)
