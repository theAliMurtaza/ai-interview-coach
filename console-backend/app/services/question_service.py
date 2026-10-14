"""Seed or AI question generation, persistence, and bounded follow-ups."""

import random
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.interview import DifficultyLevel, InterviewType, Question
from app.services.question_bank_data import (
    BEHAVIORAL,
    SYSTEM_DESIGN,
    SeedQuestion,
    get_technical_pool,
)


class QuestionService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def _collect_pool(
        self, *, role: str, interview_type: InterviewType, difficulty: DifficultyLevel
    ) -> list[SeedQuestion]:
        if interview_type == InterviewType.BEHAVIORAL:
            return BEHAVIORAL
        if interview_type == InterviewType.SYSTEM_DESIGN:
            return SYSTEM_DESIGN
        if interview_type == InterviewType.MIXED:
            return get_technical_pool(role, difficulty.value) + BEHAVIORAL + SYSTEM_DESIGN
        return get_technical_pool(role, difficulty.value)

    def build_question_set(
        self,
        *,
        role: str,
        interview_type: InterviewType,
        difficulty: DifficultyLevel,
        count: int,
        specialties: list[str] | None = None,
        start_index: int = 0,
    ) -> list[SeedQuestion]:
        if specialties:
            from app.services.specialty_questions import specialty_question_set

            return specialty_question_set(
                specialties=specialties,
                interview_type=interview_type,
                difficulty=difficulty,
                count=count,
                start_index=start_index,
            )
        pool = self._collect_pool(role=role, interview_type=interview_type, difficulty=difficulty)
        if not pool:
            return []

        result = list(pool)
        random.shuffle(result)
        while len(result) < count:
            batch = list(pool)
            random.shuffle(batch)
            if batch and result and batch[0] == result[-1]:
                batch[0], batch[min(1, len(batch) - 1)] = (
                    batch[min(1, len(batch) - 1)],
                    batch[0],
                )
            result.extend(batch)
        return result[:count]

    async def generate_questions_with_llm(
        self,
        *,
        role: str,
        interview_type: InterviewType,
        difficulty: DifficultyLevel,
        count: int,
        specialties: list[str] | None = None,
    ) -> list[SeedQuestion]:
        from app.agents.llm_provider import get_llm_provider
        from app.agents.prompts.question_generation import SYSTEM_PROMPT, build_prompt
        from app.core.exceptions import ServiceUnavailableError
        from app.schemas.question import QuestionBatch

        batch = await get_llm_provider().generate_structured(
            build_prompt(
                role=role,
                interview_type=interview_type.value,
                difficulty=difficulty.value,
                count=count,
                specialties=specialties,
            ),
            response_model=QuestionBatch,
            system=SYSTEM_PROMPT,
        )
        if len(batch.questions) != count:
            raise ServiceUnavailableError("AI provider returned an incorrect question count")
        return [question.model_dump() for question in batch.questions]

    async def persist_question_set(
        self, *, interview_id: uuid.UUID, seeds: list[SeedQuestion]
    ) -> list[Question]:
        questions = [
            Question(
                interview_id=interview_id,
                order_index=i * 2,
                text=seed["text"],
                expected_concepts=seed["expected_concepts"],
                follow_up_hint=seed.get("follow_up_hint"),
            )
            for i, seed in enumerate(seeds)
        ]
        self.db.add_all(questions)
        await self.db.flush()
        for q in questions:
            await self.db.refresh(q)
        return questions

    async def create_follow_up(self, *, parent: Question, text: str) -> Question:
        follow_up = Question(
            interview_id=parent.interview_id,
            order_index=parent.order_index + 1,
            text=text,
            expected_concepts=parent.expected_concepts,
            is_follow_up=True,
            parent_question_id=parent.id,
        )
        self.db.add(follow_up)
        await self.db.flush()
        await self.db.refresh(follow_up)
        return follow_up
