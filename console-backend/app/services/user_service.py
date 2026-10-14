import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, user_id: str | uuid.UUID) -> User | None:
        try:
            uid = uuid.UUID(str(user_id))
        except ValueError:
            return None
        return await self.db.get(User, uid)

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email.strip().lower()))
        return result.scalar_one_or_none()

    async def create(
        self, *, email: str, hashed_password: str | None, full_name: str | None = None
    ) -> User:
        user = User(
            email=email.strip().lower(), hashed_password=hashed_password, full_name=full_name
        )
        self.db.add(user)
        await self.db.flush()
        return user

    async def update(self, user: User, *, full_name: str | None = None) -> User:
        if full_name is not None:
            user.full_name = full_name
        await self.db.commit()
        await self.db.refresh(user)
        return user
