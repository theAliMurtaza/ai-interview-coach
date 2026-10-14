"""
Resume <-> Job Description semantic matching service.
Compares resume skills and experience against JD requirements using vector embeddings
and set overlap for skill gap analysis.
"""

from __future__ import annotations

import math
import uuid

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.rag.embeddings import embed_text
from app.core.config import settings
from app.schemas.matching import MatchResponse
from app.services.job_service import JobService
from app.services.resume_service import ResumeService


def _cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    dot = sum(a * b for a, b in zip(vec_a, vec_b, strict=True))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return max(0.0, min(1.0, dot / (norm_a * norm_b)))


class MatchingService:
    @classmethod
    async def match_resume_to_job(
        cls,
        user_id: uuid.UUID,
        resume_id: uuid.UUID,
        job_id: uuid.UUID,
        db: AsyncSession,
    ) -> MatchResponse:
        resume = await ResumeService.get_by_id(resume_id, user_id, db)
        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")

        job = await JobService.get_by_id(job_id, user_id, db)
        if not job:
            raise HTTPException(status_code=404, detail="Job description not found")

        resume_skills_lower = {s.lower() for s in resume.skills}
        matched_skills: list[str] = []
        missing_skills: list[str] = []

        for req in job.required_skills:
            if req.lower() in resume_skills_lower:
                matched_skills.append(req)
            else:
                missing_skills.append(req)

        total_req = len(job.required_skills)
        keyword_score = len(matched_skills) / total_req * 100 if total_req else 0.0
        final_score = round(keyword_score, 1)
        method = "keyword coverage"
        if settings.AI_ENABLED:
            resume_emb = await embed_text(resume.raw_text[:8000])
            job_emb = await embed_text(job.raw_text[:8000])
            final_score = round(
                0.4 * keyword_score + 0.6 * _cosine_similarity(resume_emb, job_emb) * 100, 1
            )
            method = "semantic and keyword alignment"

        recommendations = [
            f"Practice interview questions on: {skill}" for skill in missing_skills[:4]
        ]
        summary = (
            f"Candidate matches {len(matched_skills)} of {total_req} core required skills. "
            f"Overall {method} with '{job.title}' is {final_score}%."
        )

        return MatchResponse(
            resume_id=resume.id,
            job_id=job.id,
            match_score=final_score,
            matched_skills=matched_skills,
            missing_skills=missing_skills,
            recommendations=recommendations,
            summary=summary,
        )
