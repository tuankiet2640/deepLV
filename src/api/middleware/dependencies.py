import uuid

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.database import get_db
from src.api.models.api_key import APIKey
from src.api.models.user import User
from src.api.services.auth import decode_access_token, get_api_key_by_hash, get_user_by_id, hash_api_key


async def get_current_user(
    authorization: str = Header(..., alias="Authorization"),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and validate JWT from Authorization header."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authorization header")

    token = authorization[7:]
    user_id = decode_access_token(token)
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    user = await get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return user


async def get_api_key(
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
) -> APIKey:
    """Validate API key from X-API-Key header."""
    key_hash = hash_api_key(x_api_key)
    api_key = await get_api_key_by_hash(db, key_hash)
    if api_key is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    return api_key


async def get_user_from_api_key(
    api_key: APIKey = Depends(get_api_key),
    db: AsyncSession = Depends(get_db),
) -> tuple[User, APIKey]:
    """Get user associated with API key."""
    user = await get_user_by_id(db, api_key.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user, api_key
