"""
Pydantic schemas for analytics dashboard metrics.
"""

from pydantic import BaseModel


class MetricTrend(BaseModel):
    date: str
    score: float


class TopicStat(BaseModel):
    topic: str
    attempts: int
    avg_score: float
    trend: str


class DashboardSummary(BaseModel):
    total_interviews: int
    completed_interviews: int
    average_overall_score: float
    average_communication_score: float
    average_technical_score: float
    wpm_average: float
    filler_word_rate: float
    score_trends: list[MetricTrend] = []
    topic_performances: list[TopicStat] = []
