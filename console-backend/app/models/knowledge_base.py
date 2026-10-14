"""
pgvector-backed KnowledgeChunk model for RAG knowledge base.
"""

from __future__ import annotations

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class KnowledgeChunk(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "knowledge_chunks"
    __table_args__ = (
        Index(
            "ix_knowledge_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    topic: Mapped[str] = mapped_column(String(100), index=True)
    source: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    chunk_metadata: Mapped[dict] = mapped_column(JSON, default=dict)

    # 1536-dim vector for text-embedding-3-small or OpenAI embeddings
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
