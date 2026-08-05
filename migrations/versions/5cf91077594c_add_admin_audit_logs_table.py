"""add admin audit logs table

Revision ID: 5cf91077594c
Revises: f5ab9e4ef2db
Create Date: 2026-08-05 00:00:00.000000

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '5cf91077594c'
down_revision: str | None = 'f5ab9e4ef2db'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS admin_audit_logs (
            id UUID PRIMARY KEY,
            actor_user_id UUID NOT NULL,
            actor_email VARCHAR(255) NOT NULL,
            action VARCHAR(100) NOT NULL,
            target_type VARCHAR(50),
            target_id VARCHAR(255),
            details TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_admin_audit_logs_created_at "
        "ON admin_audit_logs (created_at DESC)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS admin_audit_logs")
