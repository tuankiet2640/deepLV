from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.shared.config import APISettings

settings = APISettings()

# Supabase PgBouncer (transaction mode) requires prepared_statement_cache_size=0
# Standard PostgreSQL works fine with the default settings
connect_args = {}
if "pooler.supabase.com" in settings.database_url or "supabase" in settings.database_url:
    connect_args = {"prepared_statement_cache_size": 0, "ssl": True}

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
