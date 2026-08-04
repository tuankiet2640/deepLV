"""add document result output fields

Revision ID: d7fcab8d6196
Revises: 
Create Date: 2026-08-03 17:10:22.600282

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd7fcab8d6196'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # IF NOT EXISTS: this runs on every app startup (see main.py's lifespan),
    # and a fresh database's tables are created by Base.metadata.create_all()
    # from the current models (so these columns already exist there) before
    # this migration ever runs. Only a pre-existing database predating this
    # migration is actually missing the columns.
    op.execute(
        "ALTER TABLE document_results ADD COLUMN IF NOT EXISTS translated_file_bytes BYTEA"
    )
    op.execute(
        "ALTER TABLE document_results ADD COLUMN IF NOT EXISTS output_format VARCHAR(10)"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE document_results DROP COLUMN IF EXISTS output_format")
    op.execute("ALTER TABLE document_results DROP COLUMN IF EXISTS translated_file_bytes")
