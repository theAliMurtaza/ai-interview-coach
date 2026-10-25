"""Transactional answer submission and adaptive interview progression."""

import uuid

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.interview_graph import interview_graph
from app.core.deps import get_current_active_user, get_db
from app.core.exceptions import ConflictError, ForbiddenError
from app.models.interview import DifficultyLevel, Interview, InterviewStatus, Question
from app.models.user import User
from app.schemas.answer import AnswerRead, AnswerSubmit
from app.schemas.evaluation import EvaluationRead
from app.schemas.question import QuestionRead
from app.services.answer_service import AnswerService
from app.services.interview_service import InterviewService
from app.services.question_service import QuestionService

router = APIRouter(prefix="/questions", tags=["answers"])


class AnswerResponse(BaseModel):
    answer: AnswerRead
    evaluation: EvaluationRead
    follow_up_question: QuestionRead | None = None
    next_action: str
    difficulty: DifficultyLevel


@router.post(
    "/{question_id}/answer", response_model=AnswerResponse, status_code=status.HTTP_201_CREATED
)
async def submit_answer(
    question_id: uuid.UUID,
    payload: AnswerSubmit,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> AnswerResponse:
    # Serialize all mutations of a session, including completion, on its parent row.
    interview_id = await db.scalar(select(Question.interview_id).where(Question.id == question_id))
    await db.execute(
        select(Interview)
        .where(Interview.id == interview_id, Interview.user_id == user.id)
        .with_for_update()
    )
    service = AnswerService(db)
    question = await service.get_question_or_404(question_id)
    if question.interview.user_id != user.id:
        raise ForbiddenError("This question belongs to a different user")
    if question.interview.status != InterviewStatus.IN_PROGRESS:
        raise ConflictError("Interview is no longer in progress")
    answer, evaluation = await service.submit_answer(
        question=question,
        transcript=payload.transcript,
        duration_seconds=payload.duration_seconds,
    )
    decision = await interview_graph.ainvoke(
        {
            "history": [{"score": evaluation.overall_score}],
            "difficulty": question.interview.difficulty.value,
            "follow_up_count": int(question.is_follow_up),
            "max_follow_ups": 1,
        }
    )
    follow_up = None
    if not payload.transcript.strip():
        decision["action"] = "next_question"
    if decision["action"] == "follow_up":
        follow_up = await QuestionService(db).create_follow_up(
            parent=question, text=InterviewService(db).follow_up_text(question=question)
        )
    elif decision["action"] == "adjust_difficulty":
        question.interview.difficulty = DifficultyLevel(decision["difficulty"])
        # Replace only unanswered questions so the next question reflects the new level.
        pending = (
            await db.scalars(
                select(Question)
                .where(
                    Question.interview_id == interview_id,
                    Question.id != question.id,
                    Question.is_follow_up.is_(False),
                    ~Question.answer.has(),
                )
                .order_by(Question.order_index)
            )
        ).all()
        seeds = QuestionService(db).build_question_set(
            role=question.interview.role.value,
            interview_type=question.interview.interview_type,
            difficulty=question.interview.difficulty,
            count=len(pending),
            specialties=question.interview.specialties,
            projects=question.interview.resume_projects,
            start_index=pending[0].order_index // 2 if pending else 0,
        )
        for item, seed in zip(pending, seeds, strict=True):
            item.text = seed["text"]
            item.expected_concepts = seed["expected_concepts"]
            item.follow_up_hint = seed.get("follow_up_hint")
    await db.commit()
    return AnswerResponse(
        answer=AnswerRead.model_validate(answer),
        evaluation=EvaluationRead.model_validate(evaluation),
        follow_up_question=QuestionRead.model_validate(follow_up) if follow_up else None,
        next_action=decision["action"],
        difficulty=question.interview.difficulty,
    )
