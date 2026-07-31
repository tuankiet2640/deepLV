"""MarianMT provider - wraps the existing worker HTTP call."""

import httpx
import structlog

from src.api.services.providers.base import ProviderError, TranslationProvider

log = structlog.get_logger()


class MarianMTProvider(TranslationProvider):
    """Built-in MarianMT translation via the model worker service.

    This is the default (free) provider that uses locally-hosted
    MarianMT models via the worker service.
    """

    provider_name = "marianmt"

    def __init__(self, worker_url: str):
        self.worker_url = worker_url

    async def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """Translate using the MarianMT worker service."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{self.worker_url}/translate",
                    json={
                        "text": text,
                        "source_lang": source_lang,
                        "target_lang": target_lang,
                    },
                )
        except httpx.ConnectError:
            raise ProviderError(self.provider_name, "Translation service unavailable")
        except httpx.TimeoutException:
            raise ProviderError(self.provider_name, "Translation timed out")

        if resp.status_code != 200:
            log.error("marianmt_worker_error", status=resp.status_code, body=resp.text)
            raise ProviderError(self.provider_name, "Translation failed")

        result = resp.json()
        return result["translated_text"]

    async def validate_key(self) -> bool:
        """MarianMT has no API key - just check worker is reachable."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.worker_url}/health")
                return resp.status_code == 200
        except Exception:
            return False
