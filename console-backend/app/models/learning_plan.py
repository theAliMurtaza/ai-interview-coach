"""
AI-generated learning plan database model.
"""

from __future__ import annotations

import uuid

from sqlalchemy import JSON, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class LearningPlan(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "learning_plans"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(255), default="Personalized Career Learning Plan")
    duration_days: Mapped[int] = mapped_column(Integer, default=14)
    focus_topics: Mapped[list[str]] = mapped_column(JSON, default=list)
    daily_tasks: Mapped[list[dict]] = mapped_column(JSON, default=list)
    milestones: Mapped[list[dict]] = mapped_column(JSON, default=list)
    based_on_interview_ids: Mapped[list[str]] = mapped_column(JSON, default=list)

    user: Mapped[User] = relationship("User", backref="learning_plans")  # noqa: F821
