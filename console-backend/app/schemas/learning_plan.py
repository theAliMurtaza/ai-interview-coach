"""
Pydantic schemas for AI-generated learning plans.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LearningPlanCreateRequest(BaseModel):
    duration_days: int = Field(14, ge=7, le=60)
    focus_topics: list[str] = Field(default_factory=list, max_length=10)


class LearningPlanResponse(BaseModel):
    id: uuid.UUID
    title: str
    duration_days: int
    focus_topics: list[str] = Field(default_factory=list, max_length=10)
    daily_tasks: list[dict] = []
    milestones: list[dict] = []
    based_on_interview_ids: list[str] = []
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
