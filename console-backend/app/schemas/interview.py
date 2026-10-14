import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from app.models.interview import DifficultyLevel, InterviewRole, InterviewStatus, InterviewType
from app.schemas.answer import AnswerRead
from app.schemas.evaluation import EvaluationRead
from app.schemas.question import QuestionRead


class InterviewCreate(BaseModel):
    role: InterviewRole
    interview_type: InterviewType
    difficulty: DifficultyLevel
    question_count: int = Field(default=6, ge=3, le=40)
    resume_id: uuid.UUID | None = None
    specialties: (
        list[Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]]
        | None
    ) = Field(default=None, max_length=20)

    @field_validator("specialties")
    @classmethod
    def normalize_specialties(cls, values):
        if values is None:
            return None
        if any(any(ord(char) < 32 or ord(char) == 127 for char in value) for value in values):
            raise ValueError("Specialties must not contain control characters")
        return list({value.casefold(): value for value in values}.values())


class InterviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: InterviewRole
    interview_type: InterviewType
    difficulty: DifficultyLevel
    question_count: int
    resume_id: uuid.UUID | None = None
    specialties: list[str] = Field(default_factory=list)
    status: InterviewStatus
    overall_score: float | None
    communication_score: float | None
    technical_score: float | None
    created_at: datetime


class AnswerDetail(AnswerRead):
    duration_seconds: float
    evaluation: EvaluationRead | None = None


class QuestionDetail(QuestionRead):
    answer: AnswerDetail | None = None


class InterviewDetail(InterviewRead):
    questions: list[QuestionDetail]
