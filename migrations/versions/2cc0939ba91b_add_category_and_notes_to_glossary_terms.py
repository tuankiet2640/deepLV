"""add category and notes to glossary terms

Revision ID: 2cc0939ba91b
Revises: 47d3cd29302f
Create Date: 2026-08-05 04:47:19.167483

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '2cc0939ba91b'
down_revision: str | None = '47d3cd29302f'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE glossary_terms ADD COLUMN IF NOT EXISTS category VARCHAR(50)")
    op.execute("ALTER TABLE glossary_terms ADD COLUMN IF NOT EXISTS notes VARCHAR(500)")


def downgrade() -> None:
    op.execute("ALTER TABLE glossary_terms DROP COLUMN IF EXISTS notes")
    op.execute("ALTER TABLE glossary_terms DROP COLUMN IF EXISTS category")
