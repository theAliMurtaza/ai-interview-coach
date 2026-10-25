"""
Core interview domain models:

  Interview (one practice session)
    └── Question (ordered, belongs to one interview)
          └── Answer (the user's transcript for that question)
                └── Evaluation (the AI's scoring of that answer)

This mirrors the frontend's session → question → answer → evaluation
shape 1:1, so the API layer barely needs to reshape anything.
"""

from __future__ import annotations

import enum
import uuid

from sqlalchemy import JSON, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class InterviewRole(str, enum.Enum):
    FRONTEND = "frontend"
    BACKEND = "backend"
    FULLSTACK = "fullstack"
    MOBILE = "mobile"
    DATA_AI = "data-ai"
    DEVOPS = "devops"
    QA = "qa"


class InterviewType(str, enum.Enum):
    TECHNICAL = "technical"
    BEHAVIORAL = "behavioral"
    SYSTEM_DESIGN = "system-design"
    MIXED = "mixed"


class DifficultyLevel(str, enum.Enum):
    INTERNSHIP = "internship"
    JUNIOR = "junior"
    MID = "mid"


class InterviewStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class Interview(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "interviews"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    role: Mapped[InterviewRole] = mapped_column(
        Enum(
            InterviewRole,
            name="interview_role",
            values_callable=lambda enum: [e.value for e in enum],
        )
    )
    interview_type: Mapped[InterviewType] = mapped_column(
        Enum(
            InterviewType,
            name="interview_type",
            values_callable=lambda enum: [e.value for e in enum],
        )
    )
    difficulty: Mapped[DifficultyLevel] = mapped_column(
        Enum(
            DifficultyLevel,
            name="difficulty_level",
            values_callable=lambda enum: [e.value for e in enum],
        )
    )
    question_count: Mapped[int] = mapped_column(Integer, default=6)
    resume_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("resumes.id", ondelete="SET NULL"), nullable=True
    )
    specialties: Mapped[list[str]] = mapped_column(JSON, default=list, server_default="[]")
    resume_projects: Mapped[list[dict]] = mapped_column(JSON, default=list, server_default="[]")
    status: Mapped[InterviewStatus] = mapped_column(
        Enum(
            InterviewStatus,
            name="interview_status",
            values_callable=lambda enum: [e.value for e in enum],
        ),
        default=InterviewStatus.PENDING,
    )

    # Populated once all questions are evaluated — see
    # app/services/interview_service.py::complete_interview
    overall_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    communication_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    technical_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    user: Mapped[User] = relationship(back_populates="interviews")  # noqa: F821
    questions: Mapped[list[Question]] = relationship(
        back_populates="interview", cascade="all, delete-orphan", order_by="Question.order_index"
    )


class Question(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "questions"

    interview_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("interviews.id", ondelete="CASCADE"), index=True
    )
    order_index: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)

    # Concepts an LLM (or the current heuristic evaluator) checks for in
    # the answer — see app/services/evaluation_service.py
    expected_concepts: Mapped[list[str]] = mapped_column(JSON, default=list)
    follow_up_hint: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_follow_up: Mapped[bool] = mapped_column(default=False)
    parent_question_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("questions.id", ondelete="SET NULL"), nullable=True, unique=True
    )

    interview: Mapped[Interview] = relationship(back_populates="questions")
    answer: Mapped[Answer | None] = relationship(
        back_populates="question", cascade="all, delete-orphan", uselist=False
    )


class Answer(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "answers"

    question_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), unique=True
    )
    transcript: Mapped[str] = mapped_column(Text)
    duration_seconds: Mapped[float] = mapped_column(Float)
    word_count: Mapped[int] = mapped_column(Integer, default=0)

    audio_file_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    question: Mapped[Question] = relationship(back_populates="answer")
    evaluation: Mapped[Evaluation | None] = relationship(
        back_populates="answer", cascade="all, delete-orphan", uselist=False
    )


class Evaluation(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "evaluations"

    answer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("answers.id", ondelete="CASCADE"), unique=True
    )

    overall_score: Mapped[float] = mapped_column(Float)
    communication_score: Mapped[float] = mapped_column(Float)
    technical_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    star_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    wpm: Mapped[int] = mapped_column(Integer)
    filler_count: Mapped[int] = mapped_column(Integer)
    filler_breakdown: Mapped[dict] = mapped_column(JSON, default=dict)
    concepts_hit: Mapped[list[str]] = mapped_column(JSON, default=list)
    concepts_missed: Mapped[list[str]] = mapped_column(JSON, default=list)

    # Free-text written feedback — heuristic-generated today, LLM-generated
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    assessment: Mapped[dict] = mapped_column(JSON, default=dict, server_default="{}")

    answer: Mapped[Answer] = relationship(back_populates="evaluation")
