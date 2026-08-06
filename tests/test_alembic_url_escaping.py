"""Regression test for migrations/env.py's %-escaping of DATABASE_URL.

Supabase pooler passwords are URL-encoded and routinely contain literal
%-sequences (e.g. %29 for ")"). Alembic's Config.set_main_option stores
values in a ConfigParser, which treats a bare % as an interpolation escape
and raises ValueError on anything else -- this broke every migration run
in production once the DB password happened to contain a %-sequence.
"""

from alembic.config import Config


def test_url_with_percent_survives_set_main_option_when_escaped():
    url = "postgresql+asyncpg://user:secret%2929@host.example.com:6543/db"

    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", url.replace("%", "%%"))

    assert cfg.get_main_option("sqlalchemy.url") == url


def test_url_with_unescaped_percent_raises():
    """Documents the failure mode migrations/env.py's .replace() guards against."""
    url = "postgresql+asyncpg://user:secret%2929@host.example.com:6543/db"

    cfg = Config("alembic.ini")
    try:
        cfg.set_main_option("sqlalchemy.url", url)
        raised = False
    except ValueError:
        raised = True

    assert raised, "expected ConfigParser to reject an unescaped % in the URL"
