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
    op.add_column(
        "document_results", sa.Column("translated_file_bytes", sa.LargeBinary(), nullable=True)
    )
    op.add_column(
        "document_results", sa.Column("output_format", sa.String(length=10), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("document_results", "output_format")
    op.drop_column("document_results", "translated_file_bytes")
