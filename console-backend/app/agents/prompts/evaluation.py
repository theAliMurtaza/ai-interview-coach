"""
Prompt template for LLM-graded answer evaluation (feature #5).
Pairs with app.services.evaluation_service.EvaluationService
.evaluate_with_llm as the call site.
"""

SYSTEM_PROMPT = """You are grading a spoken interview answer. Be specific \
and fair. Do not reward answers that use the right buzzwords without \
demonstrating real understanding, and do not penalize answers that are \
correct but phrased unusually."""


def build_prompt(*, question: str, transcript: str, expected_concepts: list[str]) -> str:
    concepts = ", ".join(expected_concepts) if expected_concepts else "(none specified)"
    return f"""Question: {question}

Candidate's transcribed answer: "{transcript}"

Concepts a strong answer would likely cover: {concepts}

Score the answer's technical accuracy, relevance, and depth (0-100), and \
write 1-2 sentences of specific, actionable feedback. Return JSON matching \
the EvaluationResult schema's technical_score and feedback fields \
(leave delivery metrics — wpm, filler_count, etc. — to be filled in by the \
existing deterministic evaluator; do not attempt to estimate them here)."""
