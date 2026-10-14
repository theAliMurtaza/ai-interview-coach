"""Register all ORM models for application queries and Alembic metadata."""

from app.models.base import Base  # noqa: F401
from app.models.interview import (  # noqa: F401
    Answer,
    DifficultyLevel,
    Evaluation,
    Interview,
    InterviewRole,
    InterviewStatus,
    InterviewType,
    Question,
)
from app.models.job import Job  # noqa: F401
from app.models.knowledge_base import KnowledgeChunk  # noqa: F401
from app.models.learning_plan import LearningPlan  # noqa: F401
from app.models.memory import UserTopicPerformance  # noqa: F401
from app.models.resume import Resume  # noqa: F401
from app.models.subscription import Subscription, SubscriptionStatus  # noqa: F401
from app.models.user import RefreshToken, SubscriptionPlan, User  # noqa: F401

__all__ = [
    "Base",
    "User",
    "RefreshToken",
    "SubscriptionPlan",
    "Interview",
    "InterviewRole",
    "InterviewType",
    "DifficultyLevel",
    "InterviewStatus",
    "Question",
    "Answer",
    "Evaluation",
    "Resume",
    "Job",
    "KnowledgeChunk",
    "LearningPlan",
    "Subscription",
    "SubscriptionStatus",
    "UserTopicPerformance",
]
