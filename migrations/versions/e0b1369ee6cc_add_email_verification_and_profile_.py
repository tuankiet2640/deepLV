"""add email verification and profile fields

Revision ID: e0b1369ee6cc
Revises: d7fcab8d6196
Create Date: 2026-08-04 09:16:56.131141

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e0b1369ee6cc'
down_revision: str | None = 'd7fcab8d6196'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # IF NOT EXISTS: this runs on every app startup (see main.py's lifespan),
    # and a fresh database's tables are created by Base.metadata.create_all()
    # from the current models before this migration ever runs. Only a
    # pre-existing database predating this migration is actually missing
    # these columns.
    #
    # is_verified defaults to TRUE at the DB level so existing accounts are
    # grandfathered in as verified; new signups get is_verified=False set
    # explicitly at the application layer (see routers/auth.py register()).
    op.execute(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_verified BOOLEAN NOT NULL DEFAULT TRUE"
    )
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMPTZ")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS display_name VARCHAR(100)")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar BYTEA")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_content_type VARCHAR(50)")
    op.execute(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS default_source_lang "
        "VARCHAR(10) NOT NULL DEFAULT 'auto'"
    )
    op.execute(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS default_target_lang "
        "VARCHAR(10) NOT NULL DEFAULT 'de'"
    )
    op.execute(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS theme_preference "
        "VARCHAR(10) NOT NULL DEFAULT 'system'"
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS email_otps (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            purpose VARCHAR(20) NOT NULL DEFAULT 'verify_email',
            code_hash VARCHAR(64) NOT NULL,
            expires_at TIMESTAMPTZ NOT NULL,
            attempts INTEGER NOT NULL DEFAULT 0,
            consumed BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_email_otps_user_id ON email_otps(user_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS email_otps")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS theme_preference")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS default_target_lang")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS default_source_lang")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS avatar_content_type")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS avatar")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS display_name")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS last_login_at")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS is_verified")
