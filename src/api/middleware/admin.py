"""Admin role enforcement middleware."""

from fastapi import Depends, HTTPException, status

from src.api.middleware.dependencies import get_current_user
from src.api.models.user import User


async def get_admin_user(
    user: User = Depends(get_current_user),
) -> User:
    """Verify the current user has admin privileges.

    Raises HTTP 403 if the user is not an admin.
    """
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user
