"""Provider manager service.

Handles routing translation requests to the appropriate provider
based on user preferences, BYOK keys, and admin credits.
"""

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.models.admin_provider_key import AdminProviderKey
from src.api.models.credit_transaction import CreditTransaction
from src.api.models.provider_key import ProviderKey
from src.api.models.user import User
from src.api.services.encryption import decrypt_api_key
from src.api.services.providers.base import ProviderError, TranslationProvider
from src.api.services.providers.google_provider import GoogleProvider
from src.api.services.providers.huggingface_provider import HuggingFaceProvider
from src.api.services.providers.marianmt import MarianMTProvider
from src.api.services.providers.openai_provider import OpenAIProvider
from src.shared.config import APISettings

log = structlog.get_logger()

SUPPORTED_PROVIDERS = ["marianmt", "openai", "huggingface", "google"]

PROVIDER_INFO = [
    {
        "name": "marianmt",
        "display_name": "MarianMT (Built-in)",
        "description": "Free, locally-hosted neural machine translation",
        "requires_key": False,
        "credit_cost_per_1k_chars": 0,
    },
    {
        "name": "openai",
        "display_name": "OpenAI GPT",
        "description": "High-quality AI translation via GPT models",
        "requires_key": True,
        "credit_cost_per_1k_chars": 5,
    },
    {
        "name": "huggingface",
        "display_name": "HuggingFace",
        "description": "Translation via HuggingFace Inference API",
        "requires_key": True,
        "credit_cost_per_1k_chars": 2,
    },
    {
        "name": "google",
        "display_name": "Google Translate",
        "description": "Google Cloud Translation API",
        "requires_key": True,
        "credit_cost_per_1k_chars": 3,
    },
]


class ProviderManager:
    """Manages translation provider routing and credit deduction.

    Resolves which provider to use based on request parameters:
    1. If provider_key_id is given, use user's BYOK key
    2. If provider != marianmt and no key, use admin key with credits
    3. Default to marianmt (free)
    """

    def __init__(self, settings: APISettings):
        self.settings = settings

    async def get_provider(
        self,
        provider_name: str,
        user: User,
        db: AsyncSession,
        provider_key_id: str | None = None,
    ) -> TranslationProvider:
        """Resolve and instantiate the correct provider.

        Args:
            provider_name: The requested provider (marianmt, openai, etc.)
            user: The authenticated user making the request.
            db: Database session for looking up keys.
            provider_key_id: Optional specific user key to use.

        Returns:
            An instantiated TranslationProvider.

        Raises:
            ProviderError: If provider cannot be resolved.
        """
        if provider_name not in SUPPORTED_PROVIDERS:
            raise ProviderError(provider_name, f"Unsupported provider: {provider_name}")

        # MarianMT is always free and does not need an API key
        if provider_name == "marianmt":
            return MarianMTProvider(worker_url=self.settings.model_worker_url)

        # Try user's own key first (BYOK)
        if provider_key_id:
            return await self._resolve_user_key(provider_name, user, db, provider_key_id)

        # Fall back to admin key (requires credits)
        return await self._resolve_admin_key(provider_name, db)

    async def _resolve_user_key(
        self,
        provider_name: str,
        user: User,
        db: AsyncSession,
        provider_key_id: str,
    ) -> TranslationProvider:
        """Resolve provider using user's own BYOK key."""
        result = await db.execute(
            select(ProviderKey).where(
                ProviderKey.id == provider_key_id,
                ProviderKey.user_id == user.id,
                ProviderKey.provider == provider_name,
            )
        )
        key_record = result.scalar_one_or_none()
        if not key_record:
            raise ProviderError(provider_name, "Provider key not found or does not match provider")

        api_key = decrypt_api_key(key_record.encrypted_api_key)
        return self._create_provider(provider_name, api_key)

    async def _resolve_admin_key(self, provider_name: str, db: AsyncSession) -> TranslationProvider:
        """Resolve provider using admin-managed key (user pays credits)."""
        # Check for active admin key for this provider
        result = await db.execute(
            select(AdminProviderKey).where(
                AdminProviderKey.provider == provider_name,
                AdminProviderKey.is_active.is_(True),
            )
        )
        admin_key = result.scalar_one_or_none()
        if not admin_key:
            raise ProviderError(
                provider_name,
                f"No admin key available for {provider_name}. "
                f"Please add your own API key via /api/v1/providers/keys.",
            )

        api_key = decrypt_api_key(admin_key.encrypted_api_key)
        return self._create_provider(provider_name, api_key)

    async def deduct_credits(
        self,
        user: User,
        db: AsyncSession,
        provider_name: str,
        char_count: int,
    ) -> bool:
        """Deduct credits from user for using admin key.

        Uses an atomic database UPDATE with a WHERE clause to prevent
        race conditions where concurrent requests could overdraw the balance.

        Returns True if credits were deducted, False if insufficient.
        """
        from sqlalchemy import update

        # MarianMT is free
        if provider_name == "marianmt":
            return True

        cost_per_1k = self.settings.credit_cost_per_1k_chars
        cost = (char_count / 1000) * cost_per_1k

        # Atomic update: only deduct if balance is sufficient
        result = await db.execute(
            update(User)
            .where(User.id == user.id, User.credits_balance >= cost)
            .values(credits_balance=User.credits_balance - cost)
        )

        if result.rowcount == 0:
            return False

        # Refresh user object to reflect new balance
        await db.refresh(user)

        transaction = CreditTransaction(
            user_id=user.id,
            amount=-cost,
            transaction_type="debit",
            description=f"Translation via {provider_name} ({char_count} chars)",
        )
        db.add(transaction)
        await db.flush()

        log.info(
            "credits_deducted",
            user_id=str(user.id),
            provider=provider_name,
            cost=cost,
            remaining=user.credits_balance,
        )
        return True

    def _create_provider(self, provider_name: str, api_key: str) -> TranslationProvider:
        """Create a provider instance with the given API key."""
        if provider_name == "openai":
            return OpenAIProvider(api_key=api_key)
        elif provider_name == "huggingface":
            return HuggingFaceProvider(api_key=api_key)
        elif provider_name == "google":
            return GoogleProvider(api_key=api_key)
        else:
            raise ProviderError(provider_name, f"Cannot create provider: {provider_name}")
