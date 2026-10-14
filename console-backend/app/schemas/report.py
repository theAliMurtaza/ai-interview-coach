"""
Pydantic schemas for downloadable PDF and session report generation.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel


class ReportGenerateRequest(BaseModel):
    interview_id: uuid.UUID


class ReportResponse(BaseModel):
    interview_id: uuid.UUID
    report_title: str
    download_url: str
    generated_at: datetime
