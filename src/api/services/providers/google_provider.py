"""Google Cloud Translation provider."""

import httpx
import structlog

from src.api.services.providers.base import ProviderError, TranslationProvider

log = structlog.get_logger()

GOOGLE_TRANSLATE_URL = "https://translation.googleapis.com/language/translate/v2"


class GoogleProvider(TranslationProvider):
    """Translation via Google Cloud Translation API v2.

    Uses the REST API with an API key for authentication.
    """

    provider_name = "google"

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """Translate using Google Cloud Translation API."""
        params = {
            "key": self.api_key,
            "q": text,
            "source": source_lang,
            "target": target_lang,
            "format": "text",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(GOOGLE_TRANSLATE_URL, params=params)
        except httpx.TimeoutException:
            raise ProviderError(self.provider_name, "Google Translate request timed out")
        except httpx.ConnectError:
            raise ProviderError(
                self.provider_name, "Could not connect to Google Translate API"
            )

        if resp.status_code == 401 or resp.status_code == 403:
            raise ProviderError(self.provider_name, "Invalid Google API key")
        if resp.status_code == 429:
            raise ProviderError(self.provider_name, "Google Translate rate limit exceeded")
        if resp.status_code != 200:
            log.error("google_translate_error", status=resp.status_code, body=resp.text[:200])
            raise ProviderError(
                self.provider_name, f"Google Translate API error: {resp.status_code}"
            )

        data = resp.json()
        translations = data.get("data", {}).get("translations", [])
        if not translations:
            raise ProviderError(self.provider_name, "No translation returned from Google")

        return translations[0]["translatedText"]

    async def validate_key(self) -> bool:
        """Validate the Google API key with a simple test translation."""
        params = {
            "key": self.api_key,
            "q": "hello",
            "source": "en",
            "target": "es",
            "format": "text",
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(GOOGLE_TRANSLATE_URL, params=params)
                return resp.status_code == 200
        except Exception:
            return False
