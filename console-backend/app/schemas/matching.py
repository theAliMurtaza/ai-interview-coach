"""
Pydantic schemas for resume <-> job description matching.
"""

import uuid

from pydantic import BaseModel, Field


class MatchRequest(BaseModel):
    resume_id: uuid.UUID
    job_id: uuid.UUID


class MatchResponse(BaseModel):
    resume_id: uuid.UUID
    job_id: uuid.UUID
    match_score: float = Field(..., ge=0, le=100)
    matched_skills: list[str] = []
    missing_skills: list[str] = []
    recommendations: list[str] = []
    summary: str
