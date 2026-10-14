"""
Async SQLAlchemy 2.0 engine/session setup.

Every request gets its own AsyncSession via the `get_db` dependency in
app/core/deps.py. Models import `Base` from here.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings
from app.core.database_urls import async_engine_options

database_url, engine_options = async_engine_options(settings.DATABASE_URL)
if database_url.drivername == "postgresql+asyncpg":
    engine_options.update(
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        pool_timeout=15,
        pool_recycle=300,
    )

engine = create_async_engine(
    database_url,
    echo=False,
    pool_pre_ping=True,
    future=True,
    **engine_options,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except BaseException:
            await session.rollback()
            raise
        finally:
            await session.close()
