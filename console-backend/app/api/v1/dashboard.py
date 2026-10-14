"""
Analytics dashboard API routes.
"""

from fastapi import APIRouter, Depends
from pydantic import ValidationError
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_current_active_user, get_db
from app.core.redis import get_redis_pool
from app.models.user import User
from app.schemas.dashboard import DashboardSummary
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardSummary)
async def get_dashboard(
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> DashboardSummary:
    key = f"dashboard:v1:{user.id}"
    if settings.RATE_LIMIT_ENABLED:
        try:
            cached = await get_redis_pool().get(key)
            if cached:
                return DashboardSummary.model_validate_json(cached)
        except (RedisError, ValidationError):
            pass  # Cache is optional; the request limiter remains fail-closed.
    result = await DashboardService.get_dashboard_summary(user_id=user.id, db=db)
    if settings.RATE_LIMIT_ENABLED:
        try:
            await get_redis_pool().set(key, result.model_dump_json(), ex=30)
        except RedisError:
            pass
    return result
