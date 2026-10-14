"""
User model. Passwords are never stored in plaintext — see
app/core/security.py for hashing. `oauth_provider`/`oauth_sub` support
the optional Google OAuth login path (app/services/auth_service.py).
"""

from __future__ import annotations

import enum
import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class SubscriptionPlan(str, enum.Enum):
    FREE = "free"
    PRO = "pro"


class User(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("oauth_provider", "oauth_sub", name="uq_oauth_identity"),)

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    oauth_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    oauth_sub: Mapped[str | None] = mapped_column(String(255), nullable=True)

    plan: Mapped[SubscriptionPlan] = mapped_column(
        Enum(
            SubscriptionPlan,
            name="subscription_plan",
            values_callable=lambda enum: [e.value for e in enum],
        ),
        default=SubscriptionPlan.FREE,
    )

    interviews: Mapped[list[Interview]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan"
    )


class RefreshToken(Base, UUIDPKMixin, TimestampMixin):
    """
    Persisted refresh tokens so they can be revoked (logout / rotation)
    instead of trusting a JWT's expiry alone.
    """

    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token: Mapped[str] = mapped_column(String(512), unique=True, index=True)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
