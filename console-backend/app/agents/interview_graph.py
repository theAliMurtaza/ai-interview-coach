"""Interview decisions compiled once and invoked after each answer."""

from typing import Any, TypedDict

from langgraph.graph import END, StateGraph


class InterviewState(TypedDict, total=False):
    interview_id: str
    role: str
    difficulty: str
    history: list[dict[str, Any]]
    current_question: str | None
    follow_up_count: int
    max_follow_ups: int
    finished: bool
    action: str


def analyze_answer(state: InterviewState) -> dict:
    if state.get("finished"):
        return {"action": "end"}
    history = state.get("history", [])
    if not history:
        return {"action": "next_question"}
    score = history[-1].get("score", 70)
    count = state.get("follow_up_count", 0)
    if score < 55 and count < state.get("max_follow_ups", 1):
        return {"action": "follow_up", "follow_up_count": count + 1}
    levels = ["internship", "junior", "mid"]
    level = state.get("difficulty", "junior")
    if score > 90 and level in levels[:-1]:
        return {
            "action": "adjust_difficulty",
            "difficulty": levels[levels.index(level) + 1],
            "follow_up_count": 0,
        }
    return {"action": "next_question", "follow_up_count": 0}


builder = StateGraph(InterviewState)
builder.add_node("analyze_answer", analyze_answer)
builder.set_entry_point("analyze_answer")
builder.add_edge("analyze_answer", END)
interview_graph = builder.compile()
