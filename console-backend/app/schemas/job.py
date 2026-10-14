"""
Pydantic schemas for job description parsing and storage.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class JobCreateRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    company: str | None = Field(None, max_length=255)
    raw_text: str = Field(..., min_length=20, max_length=50000)


class JobResponse(BaseModel):
    id: uuid.UUID
    title: str
    company: str | None = None
    required_skills: list[str] = []
    preferred_skills: list[str] = []
    responsibilities: list[str] = []
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class JobParsedData(BaseModel):
    title: str | None = None
    company: str | None = None
    required_skills: list[str] = []
    preferred_skills: list[str] = []
    responsibilities: list[str] = []
