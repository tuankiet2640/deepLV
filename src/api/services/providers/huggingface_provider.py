"""HuggingFace provider - uses the Inference API for translation."""

import httpx
import structlog

from src.api.services.providers.base import ProviderError, TranslationProvider

log = structlog.get_logger()

HF_INFERENCE_URL = "https://api-inference.huggingface.co/models"


class HuggingFaceProvider(TranslationProvider):
    """Translation via HuggingFace Inference API.

    Uses Helsinki-NLP/opus-mt models hosted on HuggingFace
    for inference-based translation.
    """

    provider_name = "huggingface"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def _get_model_name(self, source_lang: str, target_lang: str) -> str:
        """Get the Helsinki-NLP model name for the language pair."""
        return f"Helsinki-NLP/opus-mt-{source_lang}-{target_lang}"

    async def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """Translate using HuggingFace Inference API."""
        model_name = self._get_model_name(source_lang, target_lang)
        url = f"{HF_INFERENCE_URL}/{model_name}"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {"inputs": text}

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(url, headers=headers, json=payload)
        except httpx.TimeoutException:
            raise ProviderError(self.provider_name, "HuggingFace request timed out")
        except httpx.ConnectError:
            raise ProviderError(self.provider_name, "Could not connect to HuggingFace API")

        if resp.status_code == 401:
            raise ProviderError(self.provider_name, "Invalid HuggingFace API key")
        if resp.status_code == 503:
            raise ProviderError(
                self.provider_name,
                "Model is loading, please try again in a few seconds",
            )
        if resp.status_code != 200:
            log.error("huggingface_error", status=resp.status_code, body=resp.text[:200])
            raise ProviderError(
                self.provider_name, f"HuggingFace API error: {resp.status_code}"
            )

        data = resp.json()
        if isinstance(data, list) and len(data) > 0:
            return data[0].get("translation_text", data[0].get("generated_text", ""))
        raise ProviderError(self.provider_name, "Unexpected response format from HuggingFace")

    async def validate_key(self) -> bool:
        """Validate the HuggingFace API key."""
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://huggingface.co/api/whoami", headers=headers
                )
                return resp.status_code == 200
        except Exception:
            return False
