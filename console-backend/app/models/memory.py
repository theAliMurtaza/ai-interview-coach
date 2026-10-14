"""
Aggregated interview topic performance and memory rollup model.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class UserTopicPerformance(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "user_topic_performances"
    __table_args__ = (UniqueConstraint("user_id", "topic", name="uq_user_topic"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    topic: Mapped[str] = mapped_column(String(100), index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=1)
    avg_score: Mapped[float] = mapped_column(Float, default=0.0)
    last_practiced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    trend: Mapped[str] = mapped_column(String(50), default="stable")  # improving, declining, stable

    user: Mapped[User] = relationship("User", backref="topic_performances")  # noqa: F821
