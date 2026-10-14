import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_active_user, get_db
from app.core.exceptions import ForbiddenError
from app.models.user import User
from app.schemas.question import QuestionRead
from app.services.answer_service import AnswerService

router = APIRouter(prefix="/questions", tags=["questions"])


@router.get("/{question_id}", response_model=QuestionRead)
async def get_question(
    question_id: uuid.UUID,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> QuestionRead:
    question = await AnswerService(db).get_question_or_404(question_id)
    if question.interview.user_id != user.id:
        raise ForbiddenError("This question belongs to a different user")
    return question
