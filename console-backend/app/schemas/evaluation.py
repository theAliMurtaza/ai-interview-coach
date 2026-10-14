import uuid

from pydantic import BaseModel, ConfigDict, Field


class EvaluationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    answer_id: uuid.UUID
    overall_score: float
    communication_score: float
    technical_score: float | None
    star_score: float | None
    wpm: int
    filler_count: int
    filler_breakdown: dict
    concepts_hit: list[str]
    concepts_missed: list[str]
    feedback: str | None


class EvaluationResult(BaseModel):
    """
    Internal shape returned by EvaluationService.evaluate() before
    persistence — mirrors the frontend's evaluationService.js output
    so the scoring logic is easy to compare side by side.
    """

    overall_score: float
    communication_score: float
    technical_score: float | None
    star_score: float | None
    wpm: int
    filler_count: int
    filler_breakdown: dict[str, int]
    concepts_hit: list[str]
    concepts_missed: list[str]
    feedback: str | None = None


class AIGrade(BaseModel):
    technical_score: float = Field(ge=0, le=100, allow_inf_nan=False)
    feedback: str = Field(min_length=1, max_length=4000)
