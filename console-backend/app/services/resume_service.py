"""
Resume processing and parsing service.
Extracts text from uploaded PDF/DOCX resumes and parses structured skills,
projects, and experience with an LLM.
"""

from __future__ import annotations

import io
import uuid
import zipfile
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.agents.llm_provider import get_llm_provider
from app.core.config import settings
from app.core.exceptions import ValidationAppError
from app.models.resume import Resume
from app.schemas.resume import ResumeParsedData
from app.services.specialty_questions import detect_skills
from app.storage.s3_client import upload_file


class ResumeService:
    @staticmethod
    def extract_text_from_bytes(filename: str, content: bytes) -> str:
        """Extract plain text from PDF or DOCX file content."""
        ext = Path(filename).suffix.lower()
        try:
            if ext == ".pdf":
                import fitz

                with fitz.open(stream=content, filetype="pdf") as doc:
                    if doc.page_count > 100 or doc.is_encrypted:
                        raise ValueError("Unsupported PDF")
                    text = "\n".join(page.get_text() for page in doc)
            elif ext == ".docx":
                import docx

                with zipfile.ZipFile(io.BytesIO(content)) as archive:
                    if sum(info.file_size for info in archive.infolist()) > 25 * 1024 * 1024:
                        raise ValueError("Expanded document too large")
                doc = docx.Document(io.BytesIO(content))
                text = "\n".join(
                    [p.text for p in doc.paragraphs]
                    + [
                        cell.text
                        for table in doc.tables
                        for row in table.rows
                        for cell in row.cells
                    ]
                )
            elif ext == ".txt":
                text = content.decode("utf-8-sig")
            else:
                raise ValueError("Unsupported extension")
        except Exception as exc:
            raise ValidationAppError(
                "Invalid document; upload a readable PDF, DOCX, or UTF-8 TXT"
            ) from exc
        text = text.strip()
        if not text or len(text) > 100000:
            raise ValidationAppError("Document must contain 1-100000 readable characters")
        return text

    @classmethod
    async def parse_resume_text(cls, raw_text: str) -> ResumeParsedData:
        """Use LLM with structured output to extract profile fields."""
        system_prompt = (
            "You are a technical recruiting specialist. Extract candidate skills, projects, "
            "experience, education, and certifications accurately from the provided resume text."
        )
        prompt = (
            f"Extract all technical details into the required schema.\n\n"
            f"Resume Text:\n{raw_text[:8000]}"
        )

        if settings.AI_ENABLED:
            llm = get_llm_provider()
            return await llm.generate_structured(
                prompt=prompt,
                response_model=ResumeParsedData,
                system=system_prompt,
            )
        else:
            return ResumeParsedData(skills=detect_skills(raw_text))

    @classmethod
    async def process_and_save(
        cls,
        user_id: uuid.UUID,
        file: UploadFile,
        db: AsyncSession,
    ) -> Resume:
        """Upload to storage, extract text, parse structured data, and persist."""
        filename = (file.filename or "").replace("\\", "/").split("/")[-1]
        if not filename or len(filename) > 255:
            raise ValidationAppError("Invalid filename")
        content = await file.read(settings.MAX_UPLOAD_BYTES + 1)
        if len(content) > settings.MAX_UPLOAD_BYTES:
            raise ValidationAppError("Document exceeds upload limit")
        raw_text = await run_in_threadpool(cls.extract_text_from_bytes, filename, content)
        parsed = await cls.parse_resume_text(raw_text)

        storage_key = f"resumes/{user_id}/{uuid.uuid4()}{Path(filename).suffix.lower()}"
        file_url = await run_in_threadpool(
            upload_file,
            storage_key,
            content,
            {
                ".pdf": "application/pdf",
                ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                ".txt": "text/plain",
            }[Path(filename).suffix.lower()],
        )
        resume = Resume(
            user_id=user_id,
            filename=filename,
            file_url=file_url,
            raw_text=raw_text,
            skills=parsed.skills,
            projects=parsed.projects,
            experience=parsed.experience,
            education=parsed.education,
            certifications=parsed.certifications,
        )

        db.add(resume)
        await db.commit()
        await db.refresh(resume)
        return resume

    @classmethod
    async def get_by_id(
        cls, resume_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession
    ) -> Resume | None:
        stmt = select(Resume).where(Resume.id == resume_id, Resume.user_id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
