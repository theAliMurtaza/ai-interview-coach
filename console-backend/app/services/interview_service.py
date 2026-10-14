"""Transactional session creation, completion, and topic memory."""

import uuid
from collections import defaultdict
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models.interview import Answer, Interview, InterviewStatus, Question
from app.models.memory import UserTopicPerformance
from app.models.user import User
from app.schemas.evaluation import EvaluationResult
from app.schemas.interview import InterviewCreate
from app.services.evaluation_service import summarize_session
from app.services.question_service import QuestionService
from app.services.resume_service import ResumeService

FOLLOW_UP_SCORE_THRESHOLD = 55
GENERIC_FOLLOW_UP_TEXT = "Can you go a bit deeper, or walk me through a concrete example?"


class InterviewService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.questions = QuestionService(db)

    async def create_interview(self, *, user: User, payload: InterviewCreate) -> Interview:
        resume = None
        if payload.resume_id:
            resume = await ResumeService.get_by_id(payload.resume_id, user.id, self.db)
            if resume is None:
                raise NotFoundError("Resume not found")
        specialties = payload.specialties
        if specialties is None:
            specialties = list(
                dict.fromkeys(
                    skill.strip()
                    for skill in (resume.skills if resume else [])
                    if isinstance(skill, str)
                    and 0 < len(skill.strip()) <= 60
                    and not any(ord(char) < 32 or ord(char) == 127 for char in skill)
                )
            )[:20]
        interview = Interview(
            id=uuid.uuid4(),
            user_id=user.id,
            role=payload.role,
            interview_type=payload.interview_type,
            difficulty=payload.difficulty,
            question_count=payload.question_count,
            resume_id=payload.resume_id,
            specialties=specialties,
            status=InterviewStatus.IN_PROGRESS,
        )
        self.db.add(interview)
        await self.db.flush()

        seeds = self.questions.build_question_set(
            role=payload.role.value,
            interview_type=payload.interview_type,
            difficulty=payload.difficulty,
            count=payload.question_count,
            specialties=specialties,
        )
        if settings.AI_ENABLED:
            seeds = await self.questions.generate_questions_with_llm(
                role=payload.role.value,
                interview_type=payload.interview_type,
                difficulty=payload.difficulty,
                count=payload.question_count,
                specialties=specialties,
            )
        await self.questions.persist_question_set(interview_id=interview.id, seeds=seeds)

        await self.db.commit()
        return await self.get_interview_or_404(interview.id, user_id=user.id, with_questions=True)

    async def get_interview_or_404(
        self, interview_id: uuid.UUID, *, user_id: uuid.UUID, with_questions: bool = False
    ) -> Interview:
        # Same lock order as answer submission. Refresh already-loaded objects after waiting.
        await self.db.execute(
            select(Interview)
            .where(Interview.id == interview_id, Interview.user_id == user_id)
            .with_for_update()
        )
        if with_questions:
            stmt = (
                select(Interview)
                .options(
                    selectinload(Interview.questions)
                    .selectinload(Question.answer)
                    .selectinload(Answer.evaluation)
                )
                .where(Interview.id == interview_id)
                .execution_options(populate_existing=True)
            )
            result = await self.db.execute(stmt)
            interview = result.scalar_one_or_none()
        else:
            interview = await self.db.get(Interview, interview_id)
        if not interview:
            raise NotFoundError("Interview not found")
        if interview.user_id != user_id:
            raise ForbiddenError("This interview belongs to a different user")
        return interview

    def should_follow_up(
        self, *, evaluation: EvaluationResult, question: Question, already_followed_up: bool
    ) -> bool:
        return not already_followed_up and evaluation.overall_score < FOLLOW_UP_SCORE_THRESHOLD

    def follow_up_text(self, *, question: Question) -> str:
        # Generic today; once app/agents/interview_graph.py exists, this
        # becomes an LLM call that reads `question.follow_up_hint` plus
        # the actual weak answer to generate a specific probe instead of
        # this one-size-fits-all line.
        return (
            f"{question.follow_up_hint} Please give a concrete example."
            if question.follow_up_hint
            else GENERIC_FOLLOW_UP_TEXT
        )

    async def complete_interview(self, interview: Interview) -> Interview:
        if interview.status == InterviewStatus.COMPLETED:
            return interview
        if interview.status != InterviewStatus.IN_PROGRESS:
            raise ConflictError("Interview is no longer in progress")
        if any(not q.answer for q in interview.questions if not q.is_follow_up):
            raise ConflictError("Answer all primary questions before completing the interview")
        evaluations = [
            EvaluationResult(
                overall_score=q.answer.evaluation.overall_score,
                communication_score=q.answer.evaluation.communication_score,
                technical_score=q.answer.evaluation.technical_score,
                star_score=q.answer.evaluation.star_score,
                wpm=q.answer.evaluation.wpm,
                filler_count=q.answer.evaluation.filler_count,
                filler_breakdown=q.answer.evaluation.filler_breakdown,
                concepts_hit=q.answer.evaluation.concepts_hit,
                concepts_missed=q.answer.evaluation.concepts_missed,
            )
            for q in interview.questions
            if q.answer and q.answer.evaluation
        ]
        summary = summarize_session(evaluations)

        interview.status = InterviewStatus.COMPLETED
        interview.overall_score = summary.get("overall_score")
        interview.communication_score = summary.get("communication_score")
        interview.technical_score = summary.get("technical_score")

        # Serialize memory rollups across different interviews of the same user.
        await self.db.execute(select(User).where(User.id == interview.user_id).with_for_update())
        scores_by_topic = defaultdict(list)
        for question in interview.questions:
            if question.answer and question.answer.evaluation:
                ev = question.answer.evaluation
                for topic in question.expected_concepts or [interview.interview_type.value]:
                    scores_by_topic[topic.lower()[:100]].append(ev.overall_score)
        for topic, scores in scores_by_topic.items():
            memory = await self.db.scalar(
                select(UserTopicPerformance)
                .where(
                    UserTopicPerformance.user_id == interview.user_id,
                    UserTopicPerformance.topic == topic,
                )
                .execution_options(populate_existing=True)
            )
            score = sum(scores) / len(scores)
            if memory is None:
                self.db.add(
                    UserTopicPerformance(
                        user_id=interview.user_id, topic=topic, attempts=1, avg_score=score
                    )
                )
            else:
                memory.trend = (
                    "improving"
                    if score > memory.avg_score + 5
                    else ("declining" if score < memory.avg_score - 5 else "stable")
                )
                memory.avg_score = (memory.avg_score * memory.attempts + score) / (
                    memory.attempts + 1
                )
                memory.attempts += 1
                memory.last_practiced_at = datetime.now(UTC)

        await self.db.commit()
        await self.db.refresh(interview)
        return interview
