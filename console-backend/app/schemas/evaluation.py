import uuid
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Percent = Annotated[float, Field(ge=0, le=100, allow_inf_nan=False)]
FeedbackItem = Annotated[str, Field(min_length=1, max_length=1000)]


class AnswerAssessment(BaseModel):
    method: Literal["keyword", "ai", "unanswered", "legacy"] = "legacy"
    correct_percentage: Percent | None = None
    incorrect_percentage: Percent | None = None
    missing_percentage: Percent | None = None
    coverage_percentage: Percent | None = None
    strengths: list[FeedbackItem] = Field(default_factory=list, max_length=8)
    corrections: list[FeedbackItem] = Field(default_factory=list, max_length=8)
    improvements: list[FeedbackItem] = Field(default_factory=list, max_length=8)


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
    assessment: AnswerAssessment = Field(default_factory=AnswerAssessment)


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
    assessment: AnswerAssessment = Field(default_factory=AnswerAssessment)


class AIGrade(BaseModel):
    technical_score: float = Field(ge=0, le=100, allow_inf_nan=False)
    feedback: str = Field(min_length=1, max_length=4000)
    correct_percentage: Percent
    incorrect_percentage: Percent
    missing_percentage: Percent
    strengths: list[FeedbackItem] = Field(max_length=8)
    corrections: list[FeedbackItem] = Field(max_length=8)
    improvements: list[FeedbackItem] = Field(min_length=1, max_length=8)

    @model_validator(mode="after")
    def validate_assessment(self):
        if (
            abs(self.correct_percentage + self.incorrect_percentage + self.missing_percentage - 100)
            > 0.1
        ):
            raise ValueError("Correct, incorrect, and missing percentages must total 100")
        if self.incorrect_percentage > 0 and not self.corrections:
            raise ValueError("Incorrect points must include specific corrections")
        return self
