"""
Learning Plan generation and retrieval service.
Synthesizes user weaknesses from memory/evaluations and grounds them
with RAG knowledge base chunks to generate actionable study roadmaps.
"""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.llm_provider import get_llm_provider
from app.agents.prompts import rag_recommendation
from app.agents.rag.retriever import retrieve
from app.core.config import settings
from app.models.learning_plan import LearningPlan
from app.models.memory import UserTopicPerformance
from app.schemas.learning_plan import LearningPlanCreateRequest


class PlanContent(BaseModel):
    recommended_topics: list[dict] = Field(min_length=1, max_length=60)
    milestones: list[dict] = Field(min_length=1, max_length=20)


class LearningPlanService:
    @classmethod
    async def create_plan(
        cls,
        user_id: uuid.UUID,
        payload: LearningPlanCreateRequest,
        db: AsyncSession,
    ) -> LearningPlan:
        # Step 1: Find weakest topics
        stmt = (
            select(UserTopicPerformance)
            .where(UserTopicPerformance.user_id == user_id)
            .order_by(UserTopicPerformance.avg_score.asc())
            .limit(4)
        )
        result = await db.execute(stmt)
        performances = list(result.scalars().all())

        weak_topics = payload.focus_topics or [p.topic for p in performances]
        if not weak_topics:
            weak_topics = payload.focus_topics or ["system_design", "fastapi", "react", "database"]

        # Step 2: Retrieve grounding chunks for weak topics
        grounding_chunks = []
        for topic in weak_topics[:3]:
            chunks = await retrieve(topic, db, topic=topic, top_k=2)
            for c in chunks:
                grounding_chunks.append(
                    {"topic": c.topic, "source": c.source, "content": c.content}
                )

        # Step 3: LLM generation with prompt
        prompt = rag_recommendation.build_prompt(
            candidate_role="Full Stack Engineer",
            target_difficulty="mid",
            identified_weaknesses=weak_topics,
            available_knowledge_chunks=grounding_chunks,
            timeframe_days=payload.duration_days,
        )

        daily_tasks: list[dict] = []
        milestones: list[dict] = []

        if settings.AI_ENABLED:
            llm = get_llm_provider()
            parsed = await llm.generate_structured(
                prompt, response_model=PlanContent, system=rag_recommendation.SYSTEM_PROMPT
            )
            daily_tasks = parsed.recommended_topics
            milestones = parsed.milestones
        else:
            for topic in weak_topics:
                daily_tasks.append(
                    {
                        "topic": topic,
                        "priority": "high",
                        "key_takeaways": [
                            f"Deep dive into {topic} core primitives",
                            "Review common pitfalls",
                        ],
                        "practice_exercise": f"Build a mini-project demonstrating {topic} mastery",
                    }
                )
            milestones = [
                {
                    "day_range": f"Day 1-{payload.duration_days // 2}",
                    "focus": "Foundational weaknesses",
                    "goals": ["Complete targeted exercises"],
                },
                {
                    "day_range": f"Day {payload.duration_days // 2 + 1}-{payload.duration_days}",
                    "focus": "Mock interviews",
                    "goals": ["Achieve > 80% on mock sessions"],
                },
            ]

        plan = LearningPlan(
            user_id=user_id,
            title=f"{payload.duration_days}-Day Targeted Mastery Plan",
            duration_days=payload.duration_days,
            focus_topics=weak_topics,
            daily_tasks=daily_tasks,
            milestones=milestones,
            based_on_interview_ids=[],
        )

        db.add(plan)
        await db.commit()
        await db.refresh(plan)
        return plan

    @classmethod
    async def get_by_id(
        cls, plan_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession
    ) -> LearningPlan | None:
        stmt = select(LearningPlan).where(
            LearningPlan.id == plan_id, LearningPlan.user_id == user_id
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
