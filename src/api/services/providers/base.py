"""Base translation provider abstract class."""

from abc import ABC, abstractmethod


class TranslationProvider(ABC):
    """Abstract base class for all translation providers.

    Each provider must implement the translate method. New providers
    can be added by subclassing and registering in the provider registry.
    """

    provider_name: str = "base"

    @abstractmethod
    async def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """Translate text from source language to target language.

        Args:
            text: The text to translate.
            source_lang: ISO 639-1 language code for source.
            target_lang: ISO 639-1 language code for target.

        Returns:
            Translated text string.

        Raises:
            ProviderError: If translation fails.
        """
        ...

    @abstractmethod
    async def validate_key(self) -> bool:
        """Validate that the provider API key is working.

        Returns:
            True if key is valid and provider is accessible.
        """
        ...


class ProviderError(Exception):
    """Raised when a provider encounters an error during translation."""

    def __init__(self, provider: str, message: str):
        self.provider = provider
        self.message = message
        super().__init__(f"[{provider}] {message}")
