"""add user active status

Revision ID: aaaca48217f2
Revises: 0fca04c35145
Create Date: 2026-08-06 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "aaaca48217f2"
down_revision: str | None = "0fca04c35145"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # server_default true so every existing account stays active on migration.
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT true")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS deactivated_at TIMESTAMPTZ")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS deactivation_reason VARCHAR(500)")


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS deactivation_reason")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS deactivated_at")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS is_active")
