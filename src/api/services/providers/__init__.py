"""Translation provider abstraction layer.

Provides a clean interface for multiple translation backends:
- MarianMT (built-in, free)
- OpenAI (GPT-4/3.5 for translation)
- HuggingFace Inference API
- Google Cloud Translation API
"""

from src.api.services.providers.base import TranslationProvider
from src.api.services.providers.google_provider import GoogleProvider
from src.api.services.providers.huggingface_provider import HuggingFaceProvider
from src.api.services.providers.marianmt import MarianMTProvider
from src.api.services.providers.openai_provider import OpenAIProvider

__all__ = [
    "TranslationProvider",
    "MarianMTProvider",
    "OpenAIProvider",
    "HuggingFaceProvider",
    "GoogleProvider",
]
