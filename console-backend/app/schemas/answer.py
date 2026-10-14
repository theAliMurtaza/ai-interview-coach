import uuid

from pydantic import BaseModel, ConfigDict, Field


class AnswerSubmit(BaseModel):
    transcript: str = Field(min_length=0, max_length=20_000)
    duration_seconds: float = Field(gt=0, le=7200, allow_inf_nan=False)
    # Set once the voice pipeline (app/services/voice_service.py) lands;
    # optional today because text-only answers are fully supported.
    audio_file_url: str | None = Field(default=None, max_length=1024)


class AnswerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    question_id: uuid.UUID
    transcript: str
    duration_seconds: float
    word_count: int
