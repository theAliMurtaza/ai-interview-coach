"""
Pydantic schemas for resume upload and parsing.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.interview import InterviewRole


class ResumeUploadResponse(BaseModel):
    id: uuid.UUID
    filename: str
    file_url: str | None = None
    skills: list[str] = []
    projects: list[dict] = []
    experience: list[dict] = []
    education: list[dict] = []
    certifications: list[str] = []
    created_at: datetime
    headline: str | None = None
    suggested_role: InterviewRole | None = None
    suggested_specialties: list[str] = []

    model_config = ConfigDict(from_attributes=True)


class ResumeParsedData(BaseModel):
    skills: list[str] = []
    projects: list[dict] = []
    experience: list[dict] = []
    education: list[dict] = []
    certifications: list[str] = []
