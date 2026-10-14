"""
Job description processing and parsing service.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.llm_provider import get_llm_provider
from app.core.config import settings
from app.models.job import Job
from app.schemas.job import JobCreateRequest, JobParsedData


class JobService:
    @classmethod
    async def parse_job_text(cls, raw_text: str) -> JobParsedData:
        """Use structured LLM output to extract JD requirements."""
        system_prompt = (
            "You are a technical recruiting specialist. Extract the job title, company name, "
            "required technical skills, preferred qualifications, and core responsibilities "
            "from the provided job description."
        )
        prompt = f"Extract structured job description fields:\n\n{raw_text[:8000]}"

        if settings.AI_ENABLED:
            llm = get_llm_provider()
            return await llm.generate_structured(
                prompt=prompt,
                response_model=JobParsedData,
                system=system_prompt,
            )
        else:
            # Explicit offline keyword extraction
            skills = [
                s.strip()
                for s in [
                    "Python",
                    "FastAPI",
                    "Docker",
                    "PostgreSQL",
                    "React",
                    "TypeScript",
                    "AWS",
                    "Kubernetes",
                ]
                if s.lower() in raw_text.lower()
            ]
            return JobParsedData(required_skills=skills, responsibilities=[raw_text[:200]])

    @classmethod
    async def create_job(
        cls,
        user_id: uuid.UUID,
        payload: JobCreateRequest,
        db: AsyncSession,
    ) -> Job:
        parsed = await cls.parse_job_text(payload.raw_text)

        title = payload.title or parsed.title or "Software Engineer"
        company = payload.company or parsed.company

        job = Job(
            user_id=user_id,
            title=title,
            company=company,
            raw_text=payload.raw_text,
            required_skills=parsed.required_skills,
            preferred_skills=parsed.preferred_skills,
            responsibilities=parsed.responsibilities,
        )

        db.add(job)
        await db.commit()
        await db.refresh(job)
        return job

    @classmethod
    async def get_by_id(cls, job_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession) -> Job | None:
        stmt = select(Job).where(Job.id == job_id, Job.user_id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
