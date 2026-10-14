"""
Test fixtures.

Tests run against an in-memory-ish SQLite file (via aiosqlite), not
Postgres — fast and dependency-free for CI. This means Postgres-only
features (pgvector similarity search, ARRAY columns, etc.) can't be
exercised here; those get integration tests against the real
docker-compose stack once they're implemented (see
app/models/knowledge_base.py's TODO).
"""

import os

os.environ["SECRET_KEY"] = "test-only-secret-key-at-least-32-characters"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["APP_ENV"] = "test"
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["AI_ENABLED"] = "false"
os.environ["DEBUG"] = "false"
os.environ["ALLOWED_HOSTS"] = '["test","localhost","127.0.0.1"]'
os.environ["BACKEND_CORS_ORIGINS"] = '["http://localhost:5173"]'
os.environ["STORAGE_BACKEND"] = "local"
os.environ["API_V1_PREFIX"] = "/api/v1"
from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 — registers all implemented models on Base.metadata
from app.core.database import Base
from app.core.deps import get_db
from app.main import app as fastapi_app

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # single shared connection — required for ":memory:" SQLite
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_maker() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        try:
            yield db_session
        except Exception:
            await db_session.rollback()
            raise

    fastapi_app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    fastapi_app.dependency_overrides.clear()
