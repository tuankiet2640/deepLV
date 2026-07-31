import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.database import get_db
from src.api.middleware.dependencies import get_current_user
from src.api.models.api_key import APIKey
from src.api.models.user import User
from src.api.services.auth import generate_api_key

log = structlog.get_logger()
router = APIRouter(prefix="/keys", tags=["api-keys"])

MAX_KEYS_PER_USER = 5


class CreateKeyRequest(BaseModel):
    name: str


class KeyResponse(BaseModel):
    id: str
    name: str
    key: str | None = None
    key_prefix: str
    created_at: str
    last_used_at: str | None = None


class KeyListResponse(BaseModel):
    keys: list[KeyResponse]


@router.post("", response_model=KeyResponse, status_code=status.HTTP_201_CREATED)
async def create_key(
    req: CreateKeyRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> KeyResponse:
    count_result = await db.execute(
        select(func.count()).select_from(APIKey).where(APIKey.user_id == user.id)
    )
    count = count_result.scalar_one()
    if count >= MAX_KEYS_PER_USER:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Maximum {MAX_KEYS_PER_USER} API keys allowed",
        )

    full_key, key_hash, key_prefix = generate_api_key()
    api_key = APIKey(
        user_id=user.id,
        name=req.name,
        key_hash=key_hash,
        key_prefix=key_prefix,
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)

    log.info("api_key_created", user_id=str(user.id), key_id=str(api_key.id))
    return KeyResponse(
        id=str(api_key.id),
        name=api_key.name,
        key=full_key,
        key_prefix=api_key.key_prefix,
        created_at=api_key.created_at.isoformat(),
    )


@router.get("", response_model=KeyListResponse)
async def list_keys(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> KeyListResponse:
    result = await db.execute(
        select(APIKey).where(APIKey.user_id == user.id).order_by(APIKey.created_at.desc())
    )
    keys = result.scalars().all()
    return KeyListResponse(
        keys=[
            KeyResponse(
                id=str(k.id),
                name=k.name,
                key_prefix=k.key_prefix,
                created_at=k.created_at.isoformat(),
                last_used_at=k.last_used_at.isoformat() if k.last_used_at else None,
            )
            for k in keys
        ]
    )


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_key(
    key_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(select(APIKey).where(APIKey.id == key_id, APIKey.user_id == user.id))
    api_key = result.scalar_one_or_none()
    if not api_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")

    await db.delete(api_key)
    await db.commit()
    log.info("api_key_revoked", user_id=str(user.id), key_id=key_id)
