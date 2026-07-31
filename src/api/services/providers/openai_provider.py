"""OpenAI provider - uses GPT models for translation."""

import httpx
import structlog

from src.api.services.providers.base import ProviderError, TranslationProvider

log = structlog.get_logger()

OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"


class OpenAIProvider(TranslationProvider):
    """Translation via OpenAI GPT models.

    Uses the chat completions API with a system prompt instructing
    the model to act as a translator.
    """

    provider_name = "openai"

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.model = model

    async def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """Translate text using OpenAI chat completions."""
        system_prompt = (
            f"You are a professional translator. Translate the following text "
            f"from {source_lang} to {target_lang}. Return ONLY the translated text, "
            f"without any explanation, notes, or additional formatting."
        )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ],
            "temperature": 0.3,
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(OPENAI_API_URL, headers=headers, json=payload)
        except httpx.TimeoutException:
            raise ProviderError(self.provider_name, "OpenAI request timed out")
        except httpx.ConnectError:
            raise ProviderError(self.provider_name, "Could not connect to OpenAI API")

        if resp.status_code == 401:
            raise ProviderError(self.provider_name, "Invalid OpenAI API key")
        if resp.status_code == 429:
            raise ProviderError(self.provider_name, "OpenAI rate limit exceeded")
        if resp.status_code != 200:
            log.error("openai_error", status=resp.status_code, body=resp.text[:200])
            raise ProviderError(self.provider_name, f"OpenAI API error: {resp.status_code}")

        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()

    async def validate_key(self) -> bool:
        """Validate the OpenAI API key by listing models."""
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get("https://api.openai.com/v1/models", headers=headers)
                return resp.status_code == 200
        except Exception:
            return False
