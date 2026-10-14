"""
Resume <-> Job Description matching API routes.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_active_user, get_db
from app.models.user import User
from app.schemas.matching import MatchRequest, MatchResponse
from app.services.matching_service import MatchingService

router = APIRouter(prefix="/matching", tags=["matching"])


@router.post("", response_model=MatchResponse, status_code=status.HTTP_200_OK)
async def match_resume_to_job(
    payload: MatchRequest,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> MatchResponse:
    return await MatchingService.match_resume_to_job(
        user_id=user.id,
        resume_id=payload.resume_id,
        job_id=payload.job_id,
        db=db,
    )
