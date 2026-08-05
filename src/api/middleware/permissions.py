"""Granular permission checks for admin endpoints, layered on top of role."""

from fastapi import Depends, HTTPException, status

from src.api.middleware.dependencies import get_current_user
from src.api.models.user import User, UserRole

PERMISSIONS: dict[str, frozenset[UserRole]] = {
    "users.view": frozenset({UserRole.SUPPORT, UserRole.ADMIN}),
    "users.edit": frozenset({UserRole.ADMIN}),
    "usage.view": frozenset({UserRole.SUPPORT, UserRole.ADMIN}),
    "provider_keys.manage": frozenset({UserRole.ADMIN}),
    "settings.manage": frozenset({UserRole.ADMIN}),
    "audit.view": frozenset({UserRole.ADMIN}),
}


def require_permission(permission: str):
    """Build a FastAPI dependency requiring the given permission.

    `permission` must be a key in PERMISSIONS -- a KeyError here is a
    programming error (typo'd permission name), not a runtime condition.
    """
    allowed_roles = PERMISSIONS[permission]

    async def _check(user: User = Depends(get_current_user)) -> User:
        if UserRole(user.role) not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return _check
