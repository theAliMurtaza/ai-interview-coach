"""
Learning plans API routes.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_active_user, get_db
from app.models.learning_plan import LearningPlan
from app.models.user import User
from app.schemas.learning_plan import LearningPlanCreateRequest, LearningPlanResponse
from app.services.learning_plan_service import LearningPlanService

router = APIRouter(prefix="/learning-plans", tags=["learning-plans"])


@router.post("", response_model=LearningPlanResponse, status_code=status.HTTP_201_CREATED)
async def create_learning_plan(
    payload: LearningPlanCreateRequest,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> LearningPlanResponse:
    return await LearningPlanService.create_plan(user_id=user.id, payload=payload, db=db)


@router.get("", response_model=list[LearningPlanResponse])
async def list_learning_plans(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0, le=100000),
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> list[LearningPlanResponse]:
    stmt = (
        select(LearningPlan)
        .where(LearningPlan.user_id == user.id)
        .order_by(LearningPlan.created_at.desc())
    )
    result = await db.execute(stmt.limit(limit).offset(offset))
    return list(result.scalars().all())


@router.get("/{plan_id}", response_model=LearningPlanResponse)
async def get_learning_plan(
    plan_id: uuid.UUID,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> LearningPlanResponse:
    plan = await LearningPlanService.get_by_id(plan_id=plan_id, user_id=user.id, db=db)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Learning plan not found")
    return plan
