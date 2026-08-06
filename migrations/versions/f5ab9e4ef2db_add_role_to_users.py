"""add role to users

Revision ID: f5ab9e4ef2db
Revises: 2cc0939ba91b
Create Date: 2026-08-05 00:00:00.000000

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'f5ab9e4ef2db'
down_revision: str | None = '2cc0939ba91b'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(20) NOT NULL DEFAULT 'user'"
    )
    op.execute("UPDATE users SET role = 'admin' WHERE is_admin = true")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS is_admin")


def downgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT false")
    op.execute("UPDATE users SET is_admin = true WHERE role = 'admin'")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS role")
