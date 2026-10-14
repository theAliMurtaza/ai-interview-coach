import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.exceptions import ConflictError, NotFoundError
from app.models.interview import Answer, Evaluation, Question
from app.services.evaluation_service import EvaluationService


class AnswerService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.evaluator = EvaluationService()

    async def submit_answer(
        self,
        *,
        question: Question,
        transcript: str,
        duration_seconds: float,
        audio_file_url: str | None = None,
    ) -> tuple[Answer, Evaluation]:
        if question.answer is not None:
            raise ConflictError("This question has already been answered")

        word_count = len(transcript.split())
        answer = Answer(
            id=uuid.uuid4(),
            question_id=question.id,
            transcript=transcript,
            duration_seconds=duration_seconds,
            word_count=word_count,
            audio_file_url=audio_file_url,
        )
        self.db.add(answer)
        await self.db.flush()  # get answer.id before creating the evaluation row

        result = self.evaluator.evaluate(
            transcript=transcript,
            duration_seconds=duration_seconds,
            expected_concepts=question.expected_concepts or [],
        )
        if settings.AI_ENABLED and transcript.strip():
            result = await self.evaluator.evaluate_with_llm(
                question_text=question.text,
                transcript=transcript,
                expected_concepts=question.expected_concepts or [],
                duration_seconds=duration_seconds,
            )
        evaluation = Evaluation(
            id=uuid.uuid4(),
            answer_id=answer.id,
            **result.model_dump(),
        )
        self.db.add(evaluation)
        await self.db.flush()
        await self.db.refresh(answer)
        await self.db.refresh(evaluation)
        return answer, evaluation

    async def get_question_or_404(self, question_id: uuid.UUID) -> Question:
        stmt = (
            select(Question)
            .options(
                selectinload(Question.interview),
                selectinload(Question.answer).selectinload(Answer.evaluation),
            )
            .where(Question.id == question_id)
            .execution_options(populate_existing=True)
        )
        result = await self.db.execute(stmt)
        question = result.scalar_one_or_none()
        if not question:
            raise NotFoundError("Question not found")
        return question
