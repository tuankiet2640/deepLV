"""Helper for recording admin audit log entries."""

import json

from sqlalchemy.ext.asyncio import AsyncSession

from src.api.models.admin_audit_log import AdminAuditLog
from src.api.models.user import User


async def record_audit_log(
    db: AsyncSession,
    actor: User,
    action: str,
    target_type: str | None = None,
    target_id: str | None = None,
    details: dict | None = None,
) -> None:
    """Append an audit log entry to the session.

    Does not commit -- the caller's own commit (for the action being audited)
    persists this row too, so the audit entry and the change it describes
    land atomically.
    """
    db.add(
        AdminAuditLog(
            actor_user_id=actor.id,
            actor_email=actor.email,
            action=action,
            target_type=target_type,
            target_id=target_id,
            details=json.dumps(details) if details is not None else None,
        )
    )
