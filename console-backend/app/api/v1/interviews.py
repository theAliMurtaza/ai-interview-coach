import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_active_user, get_db
from app.models.interview import Interview
from app.models.user import User
from app.schemas.interview import InterviewCreate, InterviewDetail, InterviewRead
from app.services.interview_service import InterviewService

router = APIRouter(prefix="/interviews", tags=["interviews"])


@router.post("", response_model=InterviewDetail, status_code=status.HTTP_201_CREATED)
async def create_interview(
    payload: InterviewCreate,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> InterviewDetail:
    interview = await InterviewService(db).create_interview(user=user, payload=payload)
    return interview


@router.get("", response_model=list[InterviewRead])
async def list_interviews(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0, le=100000),
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return list(
        (
            await db.scalars(
                select(Interview)
                .where(Interview.user_id == user.id)
                .order_by(Interview.created_at.desc(), Interview.id)
                .limit(limit)
                .offset(offset)
            )
        ).all()
    )


@router.get("/{interview_id}", response_model=InterviewDetail)
async def get_interview(
    interview_id: uuid.UUID,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> InterviewDetail:
    return await InterviewService(db).get_interview_or_404(
        interview_id, user_id=user.id, with_questions=True
    )


@router.post("/{interview_id}/complete", response_model=InterviewRead)
async def complete_interview(
    interview_id: uuid.UUID,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> InterviewRead:
    service = InterviewService(db)
    interview = await service.get_interview_or_404(
        interview_id, user_id=user.id, with_questions=True
    )
    return await service.complete_interview(interview)
