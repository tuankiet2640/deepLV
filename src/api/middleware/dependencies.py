from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.database import get_db
from src.api.models.api_key import APIKey
from src.api.models.user import User
from src.api.services.auth import (
    decode_access_token,
    get_api_key_by_hash,
    get_user_by_id,
    hash_api_key,
)


async def get_current_user(
    authorization: str = Header(..., alias="Authorization"),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and validate JWT from Authorization header."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header",
        )

    token = authorization[7:]
    user_id = decode_access_token(token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

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


async def get_user_from_api_key_or_jwt(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> tuple[User, APIKey | None]:
    """Authenticate via API key OR JWT token.

    Allows web UI users to translate without a separate API key.
    """
    # Try API key first
    api_key_header = request.headers.get("X-API-Key")
    if api_key_header and api_key_header != "demo":
        key_hash = hash_api_key(api_key_header)
        api_key = await get_api_key_by_hash(db, key_hash)
        if api_key:
            user = await get_user_by_id(db, api_key.user_id)
            if user:
                return user, api_key

    # Fall back to JWT
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]
        user_id = decode_access_token(token)
        if user_id:
            user = await get_user_by_id(db, user_id)
            if user:
                return user, None

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key or token",
    )
