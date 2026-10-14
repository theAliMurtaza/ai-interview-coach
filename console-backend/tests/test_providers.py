"""Provider contract tests use deterministic responses, never paid network calls."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pydantic import BaseModel

from app.agents.interview_graph import interview_graph
from app.agents.llm_provider import LLMProvider, OpenAIProvider
from app.core.exceptions import ServiceUnavailableError
from app.schemas.evaluation import AIGrade
from app.services.evaluation_service import EvaluationService


class Output(BaseModel):
    message: str


class FakeProvider(LLMProvider):
    async def generate_text(self, prompt, *, system=None):
        return self.text


async def test_structured_generation_validates_responses():
    provider = FakeProvider()
    provider.text = '{"message": "valid"}'
    assert (await provider.generate_structured("prompt", response_model=Output)).message == "valid"
    for invalid in ["not json", "{}", '{"message": {}}']:
        provider.text = invalid
        with pytest.raises(ServiceUnavailableError):
            await provider.generate_structured("prompt", response_model=Output)


async def test_openai_completion_and_refusal(monkeypatch):
    provider = OpenAIProvider("test-key", "gpt-4o-mini")
    try:
        choice = SimpleNamespace(finish_reason="stop", message=SimpleNamespace(content="valid"))
        mock = AsyncMock(return_value=SimpleNamespace(choices=[choice]))
        monkeypatch.setattr(provider.client.chat.completions, "create", mock)
        assert await provider.generate_text("prompt") == "valid"
        choice.finish_reason = "length"
        with pytest.raises(ServiceUnavailableError):
            await provider.generate_text("prompt")
    finally:
        await provider.client.close()


async def test_ai_evaluation_preserves_measured_duration(monkeypatch):
    provider = AsyncMock()
    provider.generate_structured.return_value = AIGrade(
        technical_score=80, feedback="Explain tradeoffs"
    )
    monkeypatch.setattr("app.agents.llm_provider.get_llm_provider", lambda: provider)
    result = await EvaluationService().evaluate_with_llm(
        question_text="Question",
        transcript="one two three four five six",
        expected_concepts=["one"],
        duration_seconds=6,
    )
    assert result.wpm == 60
    assert result.star_score == 0
    assert result.technical_score == 80


@pytest.mark.parametrize(
    "score,followups,action",
    [(0, 0, "follow_up"), (0, 1, "next_question"), (95, 0, "adjust_difficulty")],
)
async def test_graph_handles_zero_and_adapts(score, followups, action):
    result = await interview_graph.ainvoke(
        {"history": [{"score": score}], "difficulty": "junior", "follow_up_count": followups}
    )
    assert result["action"] == action


def test_silence_scores_zero_and_technical_zero_is_preserved():
    service = EvaluationService()
    assert (
        service.evaluate(
            transcript="", duration_seconds=10, expected_concepts=["SQL"]
        ).overall_score
        == 0
    )
    result = service.evaluate(
        transcript="when I built during my task as a result",
        duration_seconds=10,
        expected_concepts=["SQL"],
    )
    assert result.technical_score == 0
    assert result.overall_score == round(result.communication_score / 2)
