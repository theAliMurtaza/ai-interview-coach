import uuid

from pydantic import BaseModel, ConfigDict, Field


class QuestionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_index: int
    text: str
    is_follow_up: bool


class QuestionGenerationResult(BaseModel):
    """
    The structured shape an LLM call must return when generating
    questions — see app/agents/prompts/question_generation.py and
    app/services/question_service.py::generate_questions.
    """

    text: str = Field(min_length=5, max_length=2000)
    expected_concepts: list[str]
    follow_up_hint: str | None = None


class QuestionBatch(BaseModel):
    questions: list[QuestionGenerationResult] = Field(min_length=1, max_length=40)
