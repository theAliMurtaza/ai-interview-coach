"""Deterministic delivery metrics with optional validated AI grading."""

import re

from app.schemas.evaluation import AnswerAssessment, EvaluationResult

FILLER_WORDS = [
    "um",
    "uh",
    "umm",
    "uhh",
    "like",
    "you know",
    "sort of",
    "kind of",
    "basically",
    "actually",
    "literally",
    "i mean",
]

STAR_SIGNALS = {
    "situation": ["when i", "at my", "during", "at the time", "there was a"],
    "task": ["i needed to", "my task", "i was responsible", "the goal was"],
    "action": ["i decided", "i built", "i implemented", "i created", "i led", "i designed"],
    "result": ["as a result", "in the end", "we achieved", "this led to", "the outcome"],
}


def _count_filler_words(text: str) -> tuple[int, dict[str, int]]:
    lower = f" {text.lower()} "
    hits: dict[str, int] = {}
    total = 0
    for filler in FILLER_WORDS:
        pattern = r"\b" + re.escape(filler) + r"\b"
        matches = re.findall(pattern, lower)
        if matches:
            hits[filler] = len(matches)
            total += len(matches)
    return total, hits


def _word_count(text: str) -> int:
    return len(re.findall(r"\S+", text))


class EvaluationService:
    def evaluate(
        self,
        *,
        transcript: str,
        duration_seconds: float,
        expected_concepts: list[str],
    ) -> EvaluationResult:
        words = _word_count(transcript)
        minutes = max(duration_seconds / 60, 1 / 60)
        wpm = round(words / minutes)

        filler_count, filler_breakdown = _count_filler_words(transcript)
        filler_ratio = (filler_count / words) if words else 0.0

        lower = transcript.lower()
        concepts_hit = [
            c
            for c in expected_concepts
            if re.search(r"(?<!\w)" + re.escape(c.lower()) + r"(?!\w)", lower)
        ]
        concepts_missed = [c for c in expected_concepts if c not in concepts_hit]
        concept_coverage = (
            round((len(concepts_hit) / len(expected_concepts)) * 100) if expected_concepts else None
        )

        star_hits = {
            key: any(phrase in lower for phrase in phrases) for key, phrases in STAR_SIGNALS.items()
        }
        star_score = round((sum(star_hits.values()) / 4) * 100)

        filler_penalty = min(filler_ratio * 400, 45)
        pace_penalty = 15 if (wpm < 90 or wpm > 200) else 8 if (wpm < 100 or wpm > 180) else 0
        communication_score = max(0, round(100 - filler_penalty - pace_penalty))

        if not words:
            communication_score = 0
        technical_score = concept_coverage
        candidate_scores = (
            communication_score,
            technical_score if technical_score is not None else star_score,
        )
        scores_to_blend = [s for s in candidate_scores if s is not None]
        overall_score = round(sum(scores_to_blend) / len(scores_to_blend)) if scores_to_blend else 0

        improvements = []
        if not words:
            improvements.append(
                "Record an answer: state your approach, explain why, and give an example."
            )
        else:
            if concepts_missed:
                improvements.append(
                    "Explain these missing points in your own words: "
                    + ", ".join(concepts_missed)[:700]
                    + "."
                )
            improvements.append(
                "Give one concrete example, explain your own contribution, and describe the result."
            )
            if filler_ratio > 0.03:
                improvements.append(
                    "Replace repeated filler words with a short pause between ideas."
                )
            if wpm > 180:
                improvements.append("Slow down and separate your answer into clear steps.")
            elif wpm < 90:
                improvements.append("Rehearse a concise explanation with fewer long pauses.")
        assessment = AnswerAssessment(
            method="keyword" if words else "unanswered",
            coverage_percentage=concept_coverage,
            correct_percentage=None if words else 0,
            incorrect_percentage=None if words else 0,
            missing_percentage=(
                (100 - concept_coverage)
                if concept_coverage is not None
                else (100 if not words else None)
            ),
            improvements=improvements,
        )

        return EvaluationResult(
            overall_score=overall_score,
            communication_score=communication_score,
            technical_score=technical_score,
            star_score=star_score,
            wpm=wpm,
            filler_count=filler_count,
            filler_breakdown=filler_breakdown,
            concepts_hit=concepts_hit,
            concepts_missed=concepts_missed,
            feedback=(
                "Practice explaining the missing concepts: " + ", ".join(concepts_missed)
                if concepts_missed
                else "Use concrete examples and explain the outcome."
            ),
            assessment=assessment,
        )

    async def evaluate_with_llm(
        self,
        *,
        question_text: str,
        transcript: str,
        expected_concepts: list[str],
        duration_seconds: float,
    ) -> EvaluationResult:
        from app.agents.llm_provider import get_llm_provider
        from app.agents.prompts.evaluation import SYSTEM_PROMPT, build_prompt
        from app.schemas.evaluation import AIGrade

        deterministic = self.evaluate(
            transcript=transcript,
            duration_seconds=duration_seconds,
            expected_concepts=expected_concepts,
        )
        grade = await get_llm_provider().generate_structured(
            build_prompt(
                question=question_text, transcript=transcript, expected_concepts=expected_concepts
            ),
            response_model=AIGrade,
            system=SYSTEM_PROMPT,
        )
        return deterministic.model_copy(
            update={
                "technical_score": grade.technical_score,
                "feedback": grade.feedback,
                "assessment": AnswerAssessment(
                    method="ai",
                    correct_percentage=grade.correct_percentage,
                    incorrect_percentage=grade.incorrect_percentage,
                    missing_percentage=grade.missing_percentage,
                    coverage_percentage=deterministic.assessment.coverage_percentage,
                    strengths=grade.strengths,
                    corrections=grade.corrections,
                    improvements=grade.improvements,
                ),
                "overall_score": round(
                    0.6 * grade.technical_score + 0.4 * deterministic.communication_score, 1
                ),
            }
        )


def summarize_session(evaluations: list[EvaluationResult]) -> dict:
    """Session-level rollup — mirrors the frontend's summarizeSession()."""
    if not evaluations:
        return {}

    def avg(attr: str) -> float | None:
        values = [getattr(e, attr) for e in evaluations if getattr(e, attr) is not None]
        return round(sum(values) / len(values)) if values else None

    total_fillers = sum(e.filler_count for e in evaluations)
    all_fillers: dict[str, int] = {}
    for e in evaluations:
        for word, n in e.filler_breakdown.items():
            all_fillers[word] = all_fillers.get(word, 0) + n
    top_fillers = sorted(all_fillers.items(), key=lambda kv: kv[1], reverse=True)[:5]

    return {
        "overall_score": avg("overall_score"),
        "communication_score": avg("communication_score"),
        "technical_score": avg("technical_score"),
        "avg_wpm": avg("wpm"),
        "total_fillers": total_fillers,
        "top_fillers": top_fillers,
        "question_count": len(evaluations),
    }
