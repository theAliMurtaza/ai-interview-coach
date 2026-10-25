"""Paginated performance reports with escaped, wrapped user content."""

import io
import uuid
from datetime import UTC, datetime
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.models.interview import Interview
from app.schemas.report import ReportResponse
from app.services.interview_service import InterviewService
from app.storage.s3_client import upload_file


class ReportService:
    @staticmethod
    def render_pdf_bytes(interview: Interview) -> bytes:
        buffer = io.BytesIO()
        styles = getSampleStyleSheet()
        styles["Title"].textColor = colors.HexColor("#203870")
        story = [Paragraph("Interview Performance Report", styles["Title"])]

        def paragraph(text, style="BodyText"):
            story.append(Paragraph(escape(str(text)).replace("\n", "<br/>"), styles[style]))
            story.append(Spacer(1, 10))

        paragraph(f"Interview: {interview.id}")
        paragraph(f"Role: {interview.role.value} | Level: {interview.difficulty.value}")
        paragraph(f"Status: {interview.status.value}")
        for title, score in [
            ("Overall", interview.overall_score),
            ("Communication", interview.communication_score),
            ("Technical", interview.technical_score),
        ]:
            paragraph(f"{title}: {score:.1f}/100" if score is not None else f"{title}: pending")
        for i, question in enumerate(interview.questions, 1):
            paragraph(f"Question {i}: {question.text}", "Heading3")
            if question.answer:
                paragraph(question.answer.transcript or "(No speech detected)")
                ev = question.answer.evaluation
                if ev:
                    paragraph(
                        f"Score: {ev.overall_score:.0f} | "
                        f"WPM: {ev.wpm} | Fillers: {ev.filler_count}"
                    )
                    if ev.feedback:
                        paragraph(ev.feedback)
                    assessment = ev.assessment or {}
                    if assessment.get("method") in {"ai", "unanswered"}:
                        paragraph(
                            f"Correct: {assessment.get('correct_percentage')}% | "
                            f"Incorrect: {assessment.get('incorrect_percentage')}% | "
                            f"Missing: {assessment.get('missing_percentage')}%"
                        )
                        paragraph("Rubric shares; missing requirements are not incorrect claims.")
                    else:
                        covered = assessment.get("coverage_percentage")
                        if covered is not None:
                            paragraph(f"Concepts covered: {covered}% | Missing: {100 - covered}%")
                        paragraph("Keyword coverage does not verify factual correctness.")
                    for heading, key in [
                        ("What you got right", "strengths"),
                        ("What to correct", "corrections"),
                        ("How to improve", "improvements"),
                    ]:
                        for item in assessment.get(key, []):
                            paragraph(f"{heading}: {item}")
            else:
                paragraph("Not answered")
        SimpleDocTemplate(
            buffer, title="Interview Performance Report", leftMargin=40, rightMargin=40
        ).build(story)
        return buffer.getvalue()

    @classmethod
    async def generate_and_save_report(
        cls, interview_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession
    ) -> ReportResponse:
        interview = await InterviewService(db).get_interview_or_404(
            interview_id, user_id=user_id, with_questions=True
        )
        data = await run_in_threadpool(cls.render_pdf_bytes, interview)
        key = f"reports/{user_id}/{interview.id}_report.pdf"
        url = await run_in_threadpool(upload_file, key, data, "application/pdf")
        return ReportResponse(
            interview_id=interview.id,
            report_title=f"Interview_Report_{interview.id}.pdf",
            download_url=url,
            generated_at=datetime.now(UTC),
        )
