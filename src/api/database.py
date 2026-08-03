import ssl as ssl_module
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.shared.config import APISettings

settings = APISettings()

# Always disable prepared statement caching for compatibility with PgBouncer/Supabase pooler.
# This is safe even without PgBouncer — asyncpg handles its own caching.
ssl_context = ssl_module.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl_module.CERT_NONE

connect_args: dict = {
    "prepared_statement_cache_size": 0,
    "statement_cache_size": 0,
    "ssl": ssl_context,
}

engine = create_async_engine(
    settings.database_url,
    pool_size=5,
    max_overflow=3,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args=connect_args,
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with async_session() as session:
        yield session
