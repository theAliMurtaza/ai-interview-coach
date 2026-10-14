"""
Knowledge base search, query, and Q&A API routes.
"""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.llm_provider import get_llm_provider
from app.agents.prompts import rag_qa
from app.agents.rag.retriever import retrieve
from app.core.config import settings
from app.core.deps import get_current_active_user, get_db
from app.models.user import User

router = APIRouter(prefix="/knowledge-base", tags=["knowledge-base"])


class KnowledgeChunkResponse(BaseModel):
    id: str
    topic: str
    source: str
    content: str


class QARequest(BaseModel):
    query: str = Field(min_length=2, max_length=2000)
    candidate_level: str = Field(default="Mid", max_length=50)


class QAResponse(BaseModel):
    query: str
    answer: str
    sources: list[str]


@router.get("/search", response_model=list[KnowledgeChunkResponse])
async def search_knowledge_base(
    query: str = Query(..., min_length=2, max_length=2000),
    topic: str | None = Query(None),
    top_k: int = Query(5, ge=1, le=20),
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> list[KnowledgeChunkResponse]:
    chunks = await retrieve(query=query, db=db, topic=topic, top_k=top_k)
    return [
        KnowledgeChunkResponse(
            id=str(c.id),
            topic=c.topic,
            source=c.source,
            content=c.content,
        )
        for c in chunks
    ]


@router.post("/qa", response_model=QAResponse)
async def ask_knowledge_base(
    payload: QARequest,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> QAResponse:
    chunks = await retrieve(query=payload.query, db=db, top_k=4)
    chunk_dicts = [{"topic": c.topic, "source": c.source, "content": c.content} for c in chunks]

    prompt = rag_qa.build_prompt(
        query=payload.query,
        context_chunks=chunk_dicts,
        candidate_level=payload.candidate_level,
    )

    if settings.AI_ENABLED and chunks:
        llm = get_llm_provider()
        answer = await llm.generate_text(prompt, system=rag_qa.SYSTEM_PROMPT)
    else:
        answer = "\n\n".join(c.content for c in chunks) or "No relevant references found."

    return QAResponse(
        query=payload.query,
        answer=answer,
        sources=[c.source for c in chunks],
    )
