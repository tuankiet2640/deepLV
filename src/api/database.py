import ssl as ssl_module
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.shared.config import APISettings

settings = APISettings()

# Supabase PgBouncer (transaction mode) requires prepared_statement_cache_size=0
# and SSL with verification disabled (Supabase pooler uses self-signed certs)
connect_args: dict = {}
if "pooler.supabase.com" in settings.database_url or "supabase" in settings.database_url:
    ssl_context = ssl_module.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl_module.CERT_NONE
    connect_args = {"prepared_statement_cache_size": 0, "ssl": ssl_context}

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
