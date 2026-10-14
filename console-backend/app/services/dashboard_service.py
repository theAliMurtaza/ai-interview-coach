"""
Analytics dashboard service.
Computes and aggregates user interview trends, score averages, speech velocity,
and topic masteries from UserTopicPerformance and Interview tables.
"""

from __future__ import annotations

import uuid

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.interview import Answer, Evaluation, Interview, InterviewStatus, Question
from app.models.memory import UserTopicPerformance
from app.schemas.dashboard import DashboardSummary, MetricTrend, TopicStat


class DashboardService:
    @classmethod
    async def get_dashboard_summary(cls, user_id: uuid.UUID, db: AsyncSession) -> DashboardSummary:
        completed = Interview.status == InterviewStatus.COMPLETED
        row = (
            await db.execute(
                select(
                    func.count(Interview.id),
                    func.sum(case((completed, 1), else_=0)),
                    func.avg(case((completed, Interview.overall_score))),
                    func.avg(case((completed, Interview.communication_score))),
                    func.avg(case((completed, Interview.technical_score))),
                ).where(Interview.user_id == user_id)
            )
        ).one()
        total, completed_count, avg_overall, avg_comm, avg_tech = [value or 0 for value in row]
        recent = (
            await db.scalars(
                select(Interview)
                .where(
                    Interview.user_id == user_id,
                    completed,
                )
                .order_by(Interview.created_at.desc(), Interview.id)
                .limit(10)
            )
        ).all()
        trends = [
            MetricTrend(date=i.created_at.strftime("%Y-%m-%d"), score=i.overall_score or 0)
            for i in reversed(recent)
        ]

        # Speech statistics from evaluations
        eval_stmt = (
            select(
                func.avg(Evaluation.wpm).label("avg_wpm"),
                func.avg(Evaluation.filler_count).label("avg_fillers"),
            )
            .join(Answer, Evaluation.answer_id == Answer.id)
            .join(Question, Answer.question_id == Question.id)
            .join(Interview, Question.interview_id == Interview.id)
            .where(Interview.user_id == user_id)
        )
        eval_res = await db.execute(eval_stmt)
        eval_row = eval_res.first()
        wpm = float(eval_row.avg_wpm or 0.0) if eval_row else 0.0
        filler_rate = float(eval_row.avg_fillers or 0.0) if eval_row else 0.0

        # Topic performances
        topic_stmt = select(UserTopicPerformance).where(UserTopicPerformance.user_id == user_id)
        topic_res = await db.execute(topic_stmt.order_by(UserTopicPerformance.avg_score).limit(100))
        topics = [
            TopicStat(
                topic=t.topic,
                attempts=t.attempts,
                avg_score=t.avg_score,
                trend=t.trend,
            )
            for t in topic_res.scalars().all()
        ]

        return DashboardSummary(
            total_interviews=total,
            completed_interviews=completed_count,
            average_overall_score=round(avg_overall, 1),
            average_communication_score=round(avg_comm, 1),
            average_technical_score=round(avg_tech, 1),
            wpm_average=round(wpm, 1),
            filler_word_rate=round(filler_rate, 1),
            score_trends=trends,
            topic_performances=topics,
        )
