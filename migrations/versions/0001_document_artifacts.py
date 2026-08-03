"""Add document_artifacts for format-preserving document translation.

Revision ID: 0001_document_artifacts
Revises:
Create Date: 2026-08-03

This is the first committed revision. The rest of the schema is still created by
``Base.metadata.create_all`` at API startup, so this revision covers only the new
table and guards the create: on a deployment where startup already made the
table, ``alembic upgrade head`` must be a no-op rather than an error.
"""

import sqlalchemy as sa
from alembic import op

revision = "0001_document_artifacts"
down_revision = None
branch_labels = None
depends_on = None

TABLE_NAME = "document_artifacts"


def upgrade() -> None:
    if _table_exists():
        return

    op.create_table(
        TABLE_NAME,
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=150), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("format_preserved", sa.Boolean(), nullable=False),
        sa.Column("segment_count", sa.Integer(), nullable=False),
        sa.Column("translated_segments", sa.Integer(), nullable=False),
        sa.Column("failed_segments", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["document_jobs.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("job_id"),
    )


def downgrade() -> None:
    if _table_exists():
        op.drop_table(TABLE_NAME)


def _table_exists() -> bool:
    inspector = sa.inspect(op.get_bind())
    return inspector.has_table(TABLE_NAME)
