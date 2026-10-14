"""Opt-in integration checks against a disposable PostgreSQL + pgvector database."""

import asyncio
import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import select, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.agents.rag.embeddings import EMBEDDING_MODEL
from app.agents.rag.retriever import retrieve
from app.core.config import settings
from app.models.knowledge_base import KnowledgeChunk
from app.models.user import User
from app.services.auth_service import AuthService

URL = os.environ.get("TEST_POSTGRES_URL")
pytestmark = pytest.mark.skipif(
    not URL, reason="Set TEST_POSTGRES_URL to a disposable test database"
)


async def test_postgres_migrations_vectors_and_atomic_refresh(monkeypatch):
    assert make_url(URL).database.endswith("_test"), "Integration database name must end in _test"
    env = {
        **os.environ,
        "DATABASE_URL": URL,
        "DATABASE_URL_SYNC": URL.replace("+asyncpg", "+psycopg2"),
    }
    backend = Path(__file__).resolve().parents[1]
    preflight = create_async_engine(URL)
    try:
        async with preflight.connect() as conn:
            count = await conn.scalar(
                text("SELECT count(*) FROM information_schema.tables WHERE table_schema='public'")
            )
            assert count == 0, "Use a fresh disposable database; refusing to alter existing tables"
    finally:
        await preflight.dispose()
    for args in [["upgrade", "head"], ["check"], ["downgrade", "base"], ["upgrade", "head"]]:
        result = await asyncio.to_thread(
            subprocess.run,
            [sys.executable, "-m", "alembic", *args],
            env=env,
            cwd=backend,
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0, result.stdout + result.stderr
    engine = create_async_engine(URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as db:
            tokens = await AuthService(db).register(
                email="postgres@example.com", password="safe-password123", full_name=None
            )
            user = await db.scalar(select(User).where(User.email == "postgres@example.com"))
            assert user.plan.value == "free"
            db.add_all(
                [
                    KnowledgeChunk(
                        topic="test",
                        source="a",
                        content="aligned",
                        embedding=[1.0] + [0.0] * 1535,
                        embedding_model=EMBEDDING_MODEL,
                    ),
                    KnowledgeChunk(
                        topic="test",
                        source="b",
                        content="orthogonal",
                        embedding=[0.0, 1.0] + [0.0] * 1534,
                        embedding_model=EMBEDDING_MODEL,
                    ),
                ]
            )
            await db.commit()
            monkeypatch.setattr(settings, "AI_ENABLED", True)

            async def embed(_):
                return [1.0] + [0.0] * 1535

            monkeypatch.setattr("app.agents.rag.retriever.embed_text", embed)
            assert (await retrieve("query", db, top_k=1))[0].source == "a"

        async def refresh_once():
            from app.core.exceptions import UnauthorizedError

            async with factory() as db:
                try:
                    await AuthService(db).refresh(tokens.refresh_token)
                    return "ok"
                except UnauthorizedError:
                    await db.rollback()
                    return "rejected"

        assert sorted(await asyncio.gather(refresh_once(), refresh_once())) == ["ok", "rejected"]
    finally:
        await engine.dispose()
