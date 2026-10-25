"""
Resume upload and retrieval API routes.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_active_user, get_db
from app.models.resume import Resume
from app.models.user import User
from app.schemas.resume import ResumeUploadResponse
from app.services.resume_headline import detect_resume_header
from app.services.resume_service import ResumeService

router = APIRouter(prefix="/resumes", tags=["resumes"])


def resume_response(resume: Resume) -> ResumeUploadResponse:
    # Compute from saved text so existing resumes gain detection without a migration.
    return ResumeUploadResponse.model_validate(
        {
            **ResumeUploadResponse.model_validate(resume).model_dump(),
            **detect_resume_header(resume.raw_text, resume.skills),
        }
    )


@router.post("/upload", response_model=ResumeUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_resume(
    file: UploadFile,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ResumeUploadResponse:
    if not (file.filename or "").lower().endswith((".pdf", ".docx", ".txt")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Supported formats: .pdf, .docx, .txt",
        )
    resume = await ResumeService.process_and_save(user_id=user.id, file=file, db=db)
    return resume_response(resume)


@router.get("", response_model=list[ResumeUploadResponse])
async def list_resumes(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0, le=100000),
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> list[ResumeUploadResponse]:
    stmt = select(Resume).where(Resume.user_id == user.id).order_by(Resume.created_at.desc())
    result = await db.execute(stmt.limit(limit).offset(offset))
    return [resume_response(resume) for resume in result.scalars().all()]


@router.get("/{resume_id}", response_model=ResumeUploadResponse)
async def get_resume(
    resume_id: uuid.UUID,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ResumeUploadResponse:
    resume = await ResumeService.get_by_id(resume_id=resume_id, user_id=user.id, db=db)
    if not resume:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")
    return resume_response(resume)
