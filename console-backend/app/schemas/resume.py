"""
Pydantic schemas for resume upload and parsing.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


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

    model_config = ConfigDict(from_attributes=True)


class ResumeParsedData(BaseModel):
    skills: list[str] = []
    projects: list[dict] = []
    experience: list[dict] = []
    education: list[dict] = []
    certifications: list[str] = []
