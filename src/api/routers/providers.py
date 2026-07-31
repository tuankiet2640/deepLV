"""Provider key management router.

Allows users to store their own API keys (BYOK) for external
translation providers like OpenAI, HuggingFace, and Google.
"""

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.database import get_db
from src.api.middleware.dependencies import get_current_user
from src.api.models.provider_key import ProviderKey
from src.api.models.user import User
from src.api.services.encryption import encrypt_api_key
from src.api.services.provider_manager import PROVIDER_INFO, SUPPORTED_PROVIDERS

log = structlog.get_logger()
router = APIRouter(prefix="/providers", tags=["providers"])


class StoreKeyRequest(BaseModel):
    provider: str
    api_key: str
    label: str


class ProviderKeyResponse(BaseModel):
    id: str
    provider: str
    label: str
    created_at: str


class ProviderKeyListResponse(BaseModel):
    keys: list[ProviderKeyResponse]


class ProviderInfoResponse(BaseModel):
    name: str
    display_name: str
    description: str
    requires_key: bool
    credit_cost_per_1k_chars: int


class ProvidersListResponse(BaseModel):
    providers: list[ProviderInfoResponse]


@router.get("", response_model=ProvidersListResponse)
async def list_providers() -> ProvidersListResponse:
    """List all available translation providers with pricing info."""
    return ProvidersListResponse(providers=[ProviderInfoResponse(**info) for info in PROVIDER_INFO])


@router.post("/keys", response_model=ProviderKeyResponse, status_code=status.HTTP_201_CREATED)
async def store_provider_key(
    req: StoreKeyRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProviderKeyResponse:
    """Store a user's own API key for a translation provider."""
    if req.provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported provider: {req.provider}. "
            f"Supported: {', '.join(SUPPORTED_PROVIDERS)}",
        )

    if req.provider == "marianmt":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MarianMT is a built-in provider and does not require an API key",
        )

    # Store key with encryption at rest
    provider_key = ProviderKey(
        user_id=user.id,
        provider=req.provider,
        encrypted_api_key=encrypt_api_key(req.api_key),
        label=req.label,
    )
    db.add(provider_key)
    await db.commit()
    await db.refresh(provider_key)

    log.info(
        "provider_key_stored",
        user_id=str(user.id),
        provider=req.provider,
        key_id=str(provider_key.id),
    )
    return ProviderKeyResponse(
        id=str(provider_key.id),
        provider=provider_key.provider,
        label=provider_key.label,
        created_at=provider_key.created_at.isoformat(),
    )


@router.get("/keys", response_model=ProviderKeyListResponse)
async def list_provider_keys(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProviderKeyListResponse:
    """List all stored provider keys for the current user."""
    result = await db.execute(
        select(ProviderKey)
        .where(ProviderKey.user_id == user.id)
        .order_by(ProviderKey.created_at.desc())
    )
    keys = result.scalars().all()
    return ProviderKeyListResponse(
        keys=[
            ProviderKeyResponse(
                id=str(k.id),
                provider=k.provider,
                label=k.label,
                created_at=k.created_at.isoformat(),
            )
            for k in keys
        ]
    )


@router.delete("/keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_provider_key(
    key_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a stored provider key."""
    result = await db.execute(
        select(ProviderKey).where(ProviderKey.id == key_id, ProviderKey.user_id == user.id)
    )
    key = result.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider key not found")

    await db.delete(key)
    await db.commit()
    log.info("provider_key_deleted", user_id=str(user.id), key_id=key_id)
