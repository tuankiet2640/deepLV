import asyncio
import ssl as ssl_module
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from src.api.models import Base
from src.shared.config import APISettings

config = context.config
settings = APISettings()

# Must match src/api/database.py's connect_args: disable asyncpg prepared
# statement caching for PgBouncer/Supabase pooler compatibility, and skip
# hostname verification the same way the app engine does. A prior mismatch
# here (this engine had no connect_args at all) is suspected to have
# contributed to migrations silently failing against the Supabase pooler.
_ssl_context = ssl_module.create_default_context()
_ssl_context.check_hostname = False
_ssl_context.verify_mode = ssl_module.CERT_NONE

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# set_main_option stores the value in a ConfigParser, which treats a bare
# % as the start of an interpolation escape (e.g. %(foo)s) and raises
# ValueError on any other %. Supabase pooler passwords are URL-encoded and
# routinely contain literal %-sequences (e.g. %29 for ")"), so escape %
# to %% here or a DB password with punctuation breaks every migration run.
config.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: object) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args={
            "prepared_statement_cache_size": 0,
            "statement_cache_size": 0,
            "ssl": _ssl_context,
        },
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
