from typing import AsyncIterator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from app.core.config import settings

# Tests run each case in its own event loop, so they must not share pooled connections.
engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    **({"poolclass": NullPool} if settings.environment == "test" else {}),
)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


async def check_database() -> bool:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
