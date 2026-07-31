import hashlib
import json

import redis.asyncio as redis
import structlog

from src.shared.config import APISettings

log = structlog.get_logger()
settings = APISettings()

CACHE_TTL = 86400  # 24 hours


def _cache_key(source_lang: str, target_lang: str, text: str) -> str:
    normalized = " ".join(text.strip().split())
    raw = f"{source_lang}:{target_lang}:{normalized}"
    digest = hashlib.sha256(raw.encode()).hexdigest()
    return f"translate:{digest}"


class TranslationCache:
    def __init__(self, redis_client: redis.Redis) -> None:
        self._redis = redis_client

    async def get(self, source_lang: str, target_lang: str, text: str) -> dict | None:
        key = _cache_key(source_lang, target_lang, text)
        try:
            data = await self._redis.get(key)
            if data:
                log.debug("cache_hit", key=key[:32])
                return json.loads(data)
        except redis.RedisError:
            log.warning("cache_get_error", key=key[:32], exc_info=True)
        return None

    async def set(self, source_lang: str, target_lang: str, text: str, result: dict) -> None:
        key = _cache_key(source_lang, target_lang, text)
        try:
            await self._redis.set(key, json.dumps(result), ex=CACHE_TTL)
            log.debug("cache_set", key=key[:32])
        except redis.RedisError:
            log.warning("cache_set_error", key=key[:32], exc_info=True)
