"""
Knowledge Base ingestion CLI script.
Reads markdown/text files or pre-configured seed notes, chunks them, generates embeddings,
and stores them into the pgvector knowledge_chunks table.

Run via: python -m app.agents.rag.ingest
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.rag.embeddings import EMBEDDING_MODEL, embed_text
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.knowledge_base import KnowledgeChunk

# Starter seeds across major interview categories
SEED_DOCUMENTS = [
    {
        "topic": "react",
        "source": "React Internals & Concurrency Guide",
        "content": (
            "React 18 introduces concurrent rendering features including startTransition and "
            "useDeferredValue. "
            "Unlike previous versions where rendering was synchronous and un-interruptible, "
            "concurrent React "
            "can prepare multiple versions of the UI in memory without blocking the main "
            "thread. Fiber reconciliation "
            "splits work into chunks and yields execution to high-priority browser events "
            "like typing or clicking."
        ),
    },
    {
        "topic": "fastapi",
        "source": "FastAPI & Async Concurrency Patterns",
        "content": (
            "FastAPI runs asynchronous path operations (async def) on the event loop. "
            "Synchronous route handlers (def) "
            "are executed within an anyio threadpool to prevent blocking the async loop. For "
            "IO-bound operations such as "
            "database calls or HTTP requests, use async drivers (asyncpg, httpx) to maximize "
            "throughput."
        ),
    },
    {
        "topic": "system_design",
        "source": "Distributed Caching & Cache Invalidation",
        "content": (
            "Distributed caching patterns include Cache-Aside, Write-Through, Write-Behind, "
            "and Refresh-Ahead. "
            "Cache stampede (thundering herd) happens when a popular cache key expires and "
            "thousands of requests simultaneously "
            "hit the primary database. Mitigations include probabilistic early expiration "
            "(XFetch), mutex locks, or pre-warming."
        ),
    },
    {
        "topic": "database",
        "source": "PostgreSQL Indexing & MVCC",
        "content": (
            "PostgreSQL implements Multi-Version Concurrency Control (MVCC) where updates "
            "create new tuple versions "
            "rather than mutating in place. B-tree indexes are suitable for equality and "
            "range queries, whereas GiST and GIN "
            "suit full-text search and arrays. Pgvector adds HNSW and IVFFlat vector index "
            "algorithms for nearest-neighbor search."
        ),
    },
]


async def ingest_documents(session: AsyncSession, documents: list[dict]) -> int:
    """Ingest default knowledge seeds into pgvector table."""
    count = 0
    for doc in documents:
        existing = await session.scalar(
            select(KnowledgeChunk).where(
                KnowledgeChunk.source == doc["source"], KnowledgeChunk.content == doc["content"]
            )
        )
        if existing:
            if settings.AI_ENABLED and existing.embedding_model != EMBEDDING_MODEL:
                existing.embedding = await embed_text(doc["content"])
                existing.embedding_model = EMBEDDING_MODEL
                count += 1
            continue
        emb = await embed_text(doc["content"]) if settings.AI_ENABLED else None
        chunk = KnowledgeChunk(
            topic=doc["topic"],
            source=doc["source"],
            content=doc["content"],
            chunk_metadata={"ingestion": "operator"},
            embedding=emb,
            embedding_model=EMBEDDING_MODEL if emb else None,
        )
        session.add(chunk)
        count += 1

    await session.commit()
    return count


async def ingest_seed_documents(session: AsyncSession) -> int:
    return await ingest_documents(session, SEED_DOCUMENTS)


def chunk_document(text: str, size: int = 2000, overlap: int = 200) -> list[str]:
    if not 0 <= overlap < size:
        raise ValueError("Chunk overlap must be smaller than chunk size")
    return [
        text[start : start + size]
        for start in range(0, len(text), size - overlap)
        if text[start : start + size].strip()
    ]


async def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest shared, trusted interview knowledge")
    parser.add_argument("files", nargs="*", type=Path)
    parser.add_argument("--topic", default="general")
    args = parser.parse_args()
    if len(args.topic) > 100:
        parser.error("Topic must be at most 100 characters")
    documents = list(SEED_DOCUMENTS) if not args.files else []
    for path in args.files:
        if path.suffix.lower() not in {".txt", ".md"} or path.stat().st_size > 1024 * 1024:
            parser.error("Use TXT/Markdown files no larger than 1 MiB")
        for chunk in chunk_document(path.read_text(encoding="utf-8")):
            documents.append({"topic": args.topic, "source": path.name[:255], "content": chunk})
    async with AsyncSessionLocal() as session:
        total = await ingest_documents(session, documents)
        print(f"Ingested or upgraded {total} knowledge chunks.")


if __name__ == "__main__":
    asyncio.run(main())
