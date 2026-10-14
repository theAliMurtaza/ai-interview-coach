"""Vector retrieval with an explicit lexical mode when AI is disabled."""

import re

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.rag.embeddings import EMBEDDING_MODEL, embed_text
from app.core.config import settings
from app.models.knowledge_base import KnowledgeChunk


async def retrieve(
    query: str, db: AsyncSession, *, topic: str | None = None, top_k: int = 5
) -> list[KnowledgeChunk]:
    stmt = select(KnowledgeChunk)
    if topic:
        stmt = stmt.where(KnowledgeChunk.topic == topic)
    if settings.AI_ENABLED:
        vector = await embed_text(query)
        stmt = stmt.where(
            KnowledgeChunk.embedding_model == EMBEDDING_MODEL, KnowledgeChunk.embedding.is_not(None)
        )
        stmt = stmt.order_by(KnowledgeChunk.embedding.cosine_distance(vector))
    else:
        words = list(dict.fromkeys(re.findall(r"[a-z0-9]+", query.lower())))[:20]
        if not words:
            return []
        rank = sum(
            case((func.lower(KnowledgeChunk.content).contains(word), 1), else_=0) for word in words
        )
        stmt = stmt.where(rank > 0).order_by(rank.desc(), KnowledgeChunk.id)
    return list((await db.scalars(stmt.limit(max(1, min(top_k, 20))))).all())
