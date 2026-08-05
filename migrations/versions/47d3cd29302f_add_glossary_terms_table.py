"""add glossary terms table

Revision ID: 47d3cd29302f
Revises: e0b1369ee6cc
Create Date: 2026-08-05 03:45:58.752238

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '47d3cd29302f'
down_revision: str | None = 'e0b1369ee6cc'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # IF NOT EXISTS: this runs on every app startup (see main.py's lifespan),
    # and a fresh database's tables are created by Base.metadata.create_all()
    # from the current models before this migration ever runs. Only a
    # pre-existing database predating this migration is actually missing
    # this table.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS glossary_terms (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            source_lang VARCHAR(10) NOT NULL,
            target_lang VARCHAR(10) NOT NULL,
            source_term VARCHAR(200) NOT NULL,
            target_term VARCHAR(200) NOT NULL,
            case_sensitive BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_glossary_terms_user_lang_pair "
        "ON glossary_terms(user_id, source_lang, target_lang)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS glossary_terms")
