import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_active_user, get_db
from app.core.exceptions import ForbiddenError, NotFoundError
from app.models.user import User
from app.schemas.evaluation import EvaluationRead
from app.services.answer_service import AnswerService

router = APIRouter(prefix="/questions", tags=["evaluations"])


@router.get("/{question_id}/evaluation", response_model=EvaluationRead)
async def get_evaluation(
    question_id: uuid.UUID,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> EvaluationRead:
    question = await AnswerService(db).get_question_or_404(question_id)
    if question.interview.user_id != user.id:
        raise ForbiddenError("This question belongs to a different user")
    if not question.answer or not question.answer.evaluation:
        raise NotFoundError("This question hasn't been answered yet")
    return question.answer.evaluation
