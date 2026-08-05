"""add structured fields to credit transactions

Revision ID: 0fca04c35145
Revises: 5cf91077594c
Create Date: 2026-08-05 00:00:00.000000

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0fca04c35145'
down_revision: str | None = '5cf91077594c'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE credit_transactions ADD COLUMN IF NOT EXISTS provider VARCHAR(20)")
    op.execute("ALTER TABLE credit_transactions ADD COLUMN IF NOT EXISTS char_count INTEGER")
    op.execute("ALTER TABLE credit_transactions ADD COLUMN IF NOT EXISTS rate_applied FLOAT")
    op.execute("ALTER TABLE credit_transactions ADD COLUMN IF NOT EXISTS source_lang VARCHAR(10)")
    op.execute("ALTER TABLE credit_transactions ADD COLUMN IF NOT EXISTS target_lang VARCHAR(10)")


def downgrade() -> None:
    op.execute("ALTER TABLE credit_transactions DROP COLUMN IF EXISTS target_lang")
    op.execute("ALTER TABLE credit_transactions DROP COLUMN IF EXISTS source_lang")
    op.execute("ALTER TABLE credit_transactions DROP COLUMN IF EXISTS rate_applied")
    op.execute("ALTER TABLE credit_transactions DROP COLUMN IF EXISTS char_count")
    op.execute("ALTER TABLE credit_transactions DROP COLUMN IF EXISTS provider")
