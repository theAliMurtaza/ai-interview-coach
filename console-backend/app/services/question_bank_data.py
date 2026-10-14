"""Complete seed bank shared with the frontend, stored as portable JSON."""

import json
from pathlib import Path
from typing import TypedDict


class SeedQuestion(TypedDict):
    text: str
    expected_concepts: list[str]
    follow_up_hint: str | None


def convert(question: dict) -> SeedQuestion:
    return {
        "text": question["text"],
        "expected_concepts": question["expectedConcepts"],
        "follow_up_hint": question.get("followUpHint"),
    }


_DATA = json.loads(Path(__file__).with_name("question_bank.json").read_text(encoding="utf-8"))
BEHAVIORAL = [convert(q) for q in _DATA["behavioral"]]
SYSTEM_DESIGN = [convert(q) for q in _DATA["systemDesign"]]
TECHNICAL_BY_ROLE = {
    role: {tier: [convert(q) for q in questions] for tier, questions in data["technical"].items()}
    for role, data in _DATA["byRole"].items()
}


def get_technical_pool(role: str, difficulty: str) -> list[SeedQuestion]:
    return list(TECHNICAL_BY_ROLE[role][difficulty])
