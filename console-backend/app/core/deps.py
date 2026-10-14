"""
Shared FastAPI dependencies, imported by every router in app/api/v1/.
"""

from collections.abc import AsyncGenerator

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_session
from app.core.exceptions import UnauthorizedError
from app.core.rate_limit import check_rate_limit
from app.core.security import TokenType, decode_token
from app.models.user import User
from app.services.user_service import UserService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_session():
        yield session


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not token:
        raise UnauthorizedError("Not authenticated")

    payload = decode_token(token)
    if not payload or payload.get("type") != TokenType.ACCESS.value:
        raise UnauthorizedError("Invalid or expired token")

    user_id = payload.get("sub")
    user = await UserService(db).get_by_id(user_id)
    if not user or not user.is_active:
        raise UnauthorizedError("User not found or inactive")

    await check_rate_limit(f"user:{user.id}", settings.RATE_LIMIT_PER_MINUTE)
    return user


async def get_current_active_user(user: User = Depends(get_current_user)) -> User:
    # Placeholder seam for extra checks (e.g. email verification gate)
    # without every router needing to know about them individually.
    return user
