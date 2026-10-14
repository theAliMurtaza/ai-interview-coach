import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import SubscriptionPlan


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str | None
    is_verified: bool
    plan: SubscriptionPlan


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=255)
