"""
Prompt template for whole-session qualitative feedback and analysis.
Pairs with app.services.report_service and app.services.interview_service.
"""

from typing import Any

SYSTEM_PROMPT = """You are a seasoned engineering leader, bar-raiser, and career coach. \
Synthesize a candidate's complete technical interview transcript and scoring history \
into an empowering, deeply detailed, and constructive session debrief. \
Identify root causes behind technical slips, praise authentic strengths, \
and provide practical recommendations."""


def build_prompt(
    *,
    role: str,
    difficulty: str,
    session_history: list[dict[str, Any]],
    overall_score: float | None = None,
) -> str:
    """
    Build prompt for comprehensive interview session feedback.
    """
    history_lines: list[str] = []
    for i, item in enumerate(session_history, 1):
        q = item.get("question", "")
        a = item.get("answer", "")
        eval_score = (
            item.get("score") or item.get("technical_score") or item.get("overall_score", 0)
        )
        fb = item.get("feedback", "")
        history_lines.append(
            f"Question {i}: {q}\nCandidate Answer: {a}\nScore: {eval_score}\nNotes: {fb}\n"
        )

    formatted_history = "\n---\n".join(history_lines)
    score_str = f"{overall_score:.1f}" if overall_score is not None else "Pending"

    return f"""Target Role: {role}
Target Level: {difficulty}
Session Average Score: {score_str}/100

Session Questions & Transcripts:
========================================
{formatted_history}
========================================

Instructions:
1. Deliver a high-level summary of the candidate's readiness for this level.
2. Outline top 3 authentic technical or communication strengths demonstrated.
3. Detail 2-3 specific technical gaps with exact explanations of what knowledge was missing.
4. Give next-step study actions.

Return a valid JSON object matching:
{{
  "overall_summary": "Comprehensive qualitative review",
  "strengths": ["strength 1", "strength 2", "strength 3"],
  "areas_for_improvement": ["area 1", "area 2"],
  "recommended_focus": ["topic 1", "topic 2"]
}}"""
