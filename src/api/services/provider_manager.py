"""Provider manager service.

Handles routing translation requests to the appropriate provider
based on user preferences, BYOK keys, and admin credits.
"""

from dataclasses import dataclass

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.models.admin_provider_key import AdminProviderKey
from src.api.models.admin_settings import AdminSetting
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


async def get_provider_rate(db: AsyncSession, provider_name: str) -> float:
    """Look up the live credit rate (credits per 1k chars) for a provider.

    Reads the admin-configurable override from AdminSetting first (the
    Settings tab writes here), falling back to PROVIDER_INFO's default so
    pricing works before an admin ever visits the Settings tab. This is the
    single source of truth for both what /providers displays and what
    deduct_credits actually charges -- they must never diverge.
    """
    if provider_name == "marianmt":
        return 0.0

    result = await db.execute(
        select(AdminSetting).where(AdminSetting.key == f"credit_cost_per_1k_chars_{provider_name}")
    )
    setting = result.scalar_one_or_none()
    if setting is not None:
        return float(setting.value)

    default = next(
        (p["credit_cost_per_1k_chars"] for p in PROVIDER_INFO if p["name"] == provider_name),
        0.0,
    )
    return float(default)


@dataclass
class ResolvedProvider:
    """A provider instance plus how its API key was obtained.

    ``used_own_key`` is what callers should use to decide whether to charge
    credits: BYOK translations are free, admin-key translations are not.
    """

    provider: TranslationProvider
    used_own_key: bool


class ProviderManager:
    """Manages translation provider routing and credit deduction.

    Resolves which provider to use based on request parameters:
    1. marianmt is always free and local
    2. If provider_key_id is given, use that specific BYOK key
    3. Otherwise, if the user has stored a key for this provider, use it (free)
    4. Otherwise, use the admin key and charge credits
    """

    def __init__(self, settings: APISettings):
        self.settings = settings

    async def resolve(
        self,
        provider_name: str,
        user: User | None,
        db: AsyncSession,
        provider_key_id: str | None = None,
        key_source: str = "auto",
    ) -> ResolvedProvider:
        """Resolve and instantiate the correct provider.

        Args:
            provider_name: The requested provider (marianmt, openai, etc.)
            user: The authenticated user making the request, or None for an
                anonymous request. Only marianmt supports a None user -- every
                other branch below requires a real account.
            db: Database session for looking up keys.
            provider_key_id: Optional specific user key to use. When omitted,
                any key the user has stored for this provider is used instead
                of falling straight through to the admin key.
            key_source: How to choose the key when provider_key_id is not set.
                "auto" (default) prefers the user's stored key and only spends
                credits if they have none. "admin" forces the platform admin
                key + credits even when the user has a key of their own -- the
                explicit opt-in that lets the Translate page's source picker
                offer "pay with credits" alongside "use my key".

        Returns:
            A ResolvedProvider carrying the provider and the key source.

        Raises:
            ProviderError: If provider cannot be resolved.
        """
        if provider_name not in SUPPORTED_PROVIDERS:
            raise ProviderError(provider_name, f"Unsupported provider: {provider_name}")

        # MarianMT is always free, local, and does not need an API key or a
        # real user -- it's the only provider anonymous requests can use.
        if provider_name == "marianmt":
            return ResolvedProvider(
                provider=MarianMTProvider(worker_url=self.settings.model_worker_url),
                used_own_key=False,
            )

        if user is None:
            raise ProviderError(provider_name, "Sign in to use providers other than MarianMT")

        # An explicitly chosen BYOK key wins over everything else.
        if provider_key_id:
            return ResolvedProvider(
                provider=await self._resolve_user_key(provider_name, user, db, provider_key_id),
                used_own_key=True,
            )

        # Explicit opt-in to spend credits: skip the stored-key preference and
        # go straight to the admin key even if the user has a key saved.
        if key_source == "admin":
            return ResolvedProvider(
                provider=await self._resolve_admin_key(provider_name, db),
                used_own_key=False,
            )

        # No key was named: prefer a key the user has already stored for this
        # provider before spending credits on the admin key.
        own_key = await self._resolve_stored_user_key(provider_name, user, db)
        if own_key is not None:
            return ResolvedProvider(provider=own_key, used_own_key=True)

        # Fall back to admin key (requires credits)
        return ResolvedProvider(
            provider=await self._resolve_admin_key(provider_name, db),
            used_own_key=False,
        )

    async def get_provider(
        self,
        provider_name: str,
        user: User,
        db: AsyncSession,
        provider_key_id: str | None = None,
    ) -> TranslationProvider:
        """Resolve a provider instance, discarding the key-source information."""
        resolved = await self.resolve(provider_name, user, db, provider_key_id)
        return resolved.provider

    async def _resolve_stored_user_key(
        self,
        provider_name: str,
        user: User,
        db: AsyncSession,
    ) -> TranslationProvider | None:
        """Build a provider from the user's most recent stored key, if any."""
        result = await db.execute(
            select(ProviderKey)
            .where(
                ProviderKey.user_id == user.id,
                ProviderKey.provider == provider_name,
            )
            .order_by(ProviderKey.created_at.desc())
            .limit(1)
        )
        key_record = result.scalar_one_or_none()
        if not key_record:
            return None

        log.info(
            "byok_key_auto_selected",
            user_id=str(user.id),
            provider=provider_name,
            key_id=str(key_record.id),
        )
        api_key = decrypt_api_key(key_record.encrypted_api_key)
        return self._create_provider(provider_name, api_key)

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
        # Pick any one active admin key for this provider. Nothing stops an
        # admin from adding several keys for the same provider (the create
        # endpoint doesn't dedupe), so this must NOT assume exactly one --
        # scalar_one_or_none() would raise MultipleResultsFound and 500 every
        # credit-based translation the moment a second key exists.
        result = await db.execute(
            select(AdminProviderKey)
            .where(
                AdminProviderKey.provider == provider_name,
                AdminProviderKey.is_active.is_(True),
            )
            .order_by(AdminProviderKey.created_at.desc())
            .limit(1)
        )
        admin_key = result.scalars().first()
        if admin_key:
            api_key = decrypt_api_key(admin_key.encrypted_api_key)
            return self._create_provider(provider_name, api_key)

        # Fall back to an operator-supplied key from the environment
        # (ADMIN_OPENAI_KEY / ADMIN_HUGGINGFACE_KEY / ADMIN_GOOGLE_KEY).
        env_key = self._admin_key_from_settings(provider_name)
        if env_key:
            log.info("admin_key_from_env_used", provider=provider_name)
            return self._create_provider(provider_name, env_key)

        raise ProviderError(
            provider_name,
            f"No admin key available for {provider_name}. "
            f"Please add your own API key via /api/v1/providers/keys.",
        )

    def _admin_key_from_settings(self, provider_name: str) -> str | None:
        """Read the configured admin key for a provider, if one is set."""
        env_keys = {
            "openai": self.settings.admin_openai_key,
            "huggingface": self.settings.admin_huggingface_key,
            "google": self.settings.admin_google_key,
        }
        value = env_keys.get(provider_name, "").strip()
        return value or None

    async def deduct_credits(
        self,
        user: User,
        db: AsyncSession,
        provider_name: str,
        char_count: int,
        source_lang: str | None = None,
        target_lang: str | None = None,
    ) -> float | None:
        """Deduct credits from user for using admin key, at that provider's rate.

        Uses an atomic database UPDATE with a WHERE clause to prevent
        race conditions where concurrent requests could overdraw the balance.

        Returns the amount charged, or None if the balance was insufficient.
        """
        from sqlalchemy import update

        # MarianMT is free
        if provider_name == "marianmt":
            return 0.0

        cost_per_1k = await get_provider_rate(db, provider_name)
        cost = (char_count / 1000) * cost_per_1k

        # Atomic update: only deduct if balance is sufficient
        result = await db.execute(
            update(User)
            .where(User.id == user.id, User.credits_balance >= cost)
            .values(credits_balance=User.credits_balance - cost)
        )

        if result.rowcount == 0:
            return None

        # Refresh user object to reflect new balance
        await db.refresh(user)

        transaction = CreditTransaction(
            user_id=user.id,
            amount=-cost,
            transaction_type="debit",
            description=f"Translation via {provider_name} ({char_count} chars)",
            provider=provider_name,
            char_count=char_count,
            rate_applied=cost_per_1k,
            source_lang=source_lang,
            target_lang=target_lang,
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
        return cost

    async def refund_credits(
        self,
        user: User,
        db: AsyncSession,
        amount: float,
        provider_name: str,
        reason: str,
    ) -> None:
        """Refund previously-deducted credits, e.g. a document job that
        reserved credits up front and then failed before completing.

        Unlike deduct_credits, a refund can never overdraw, so no balance
        check is needed.
        """
        from sqlalchemy import update

        await db.execute(
            update(User)
            .where(User.id == user.id)
            .values(credits_balance=User.credits_balance + amount)
        )
        await db.refresh(user)

        db.add(
            CreditTransaction(
                user_id=user.id,
                amount=amount,
                transaction_type="refund",
                description=f"Refund: {reason}",
                provider=provider_name,
            )
        )
        await db.flush()

        log.info(
            "credits_refunded",
            user_id=str(user.id),
            provider=provider_name,
            amount=amount,
            remaining=user.credits_balance,
        )

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
