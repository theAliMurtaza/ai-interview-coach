"""Resume-to-interview integration, privacy, and specialty persistence."""

import uuid
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import create_engine, text

from app.core.config import settings
from app.core.local_migrations import upgrade_local_database
from app.models.interview import DifficultyLevel, InterviewType
from app.services.question_service import QuestionService
from app.services.specialty_questions import detect_skills
from tests.test_interviews import _auth_headers

SETUP = {
    "role": "frontend",
    "interview_type": "technical",
    "difficulty": "junior",
    "question_count": 3,
}


async def test_resume_upload_select_specialties_and_ownership(client, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "LOCAL_STORAGE_DIR", str(tmp_path))
    owner = await _auth_headers(client)
    other = await _auth_headers(client, "other-resume@example.com")
    uploaded = await client.post(
        "/api/v1/resumes/upload",
        headers=owner,
        files={"file": ("resume.txt", b"Skills: React, TypeScript, GraphQL", "text/plain")},
    )
    assert uploaded.status_code == 201
    resume = uploaded.json()
    assert resume["skills"] == ["React", "TypeScript", "GraphQL"]
    assert (await client.get("/api/v1/resumes", headers=other)).json() == []
    denied = await client.post(
        "/api/v1/interviews", headers=other, json={**SETUP, "resume_id": resume["id"]}
    )
    assert denied.status_code == 404
    created = await client.post(
        "/api/v1/interviews", headers=owner, json={**SETUP, "resume_id": resume["id"]}
    )
    assert created.status_code == 201
    session = created.json()
    assert session["resume_id"] == resume["id"]
    assert session["specialties"] == resume["skills"]
    for skill, question in zip(resume["skills"], session["questions"], strict=True):
        assert skill in question["text"]
    reloaded = await client.get(f"/api/v1/interviews/{session['id']}", headers=owner)
    assert reloaded.json()["specialties"] == resume["skills"]
    # Explicit topic choices override the detected resume skills.
    customized = await client.post(
        "/api/v1/interviews",
        headers=owner,
        json={**SETUP, "resume_id": resume["id"], "specialties": [" GraphQL ", "graphql"]},
    )
    assert customized.status_code == 201
    assert customized.json()["specialties"] == ["graphql"]
    assert all("graphql" in q["text"] for q in customized.json()["questions"])
    # Explicitly clearing specialties restores general role practice.
    general = await client.post(
        "/api/v1/interviews",
        headers=owner,
        json={**SETUP, "resume_id": resume["id"], "specialties": []},
    )
    assert general.status_code == 201
    assert general.json()["specialties"] == []


@pytest.mark.parametrize("topics", [["x" * 61], ["\n"], ["React\x00"], ["topic"] * 21])
async def test_reject_invalid_specialties(client, topics):
    owner = await _auth_headers(client)
    response = await client.post(
        "/api/v1/interviews", headers=owner, json={**SETUP, "specialties": topics}
    )
    assert response.status_code == 422


async def test_missing_resume_is_rejected(client):
    owner = await _auth_headers(client)
    response = await client.post(
        "/api/v1/interviews", headers=owner, json={**SETUP, "resume_id": str(uuid.uuid4())}
    )
    assert response.status_code == 404


def test_skill_detection_uses_boundaries_and_aliases():
    assert detect_skills("digital proactive javabeans go home") == []
    assert detect_skills("C++, C#, NodeJS, postgres, Golang") == [
        "Node.js",
        "PostgreSQL",
        "C++",
        "C#",
        "Go",
    ]


@pytest.mark.parametrize("style", list(InterviewType))
@pytest.mark.parametrize("difficulty", list(DifficultyLevel))
def test_offline_topics_cover_choices_and_style(style, difficulty):
    questions = QuestionService(None).build_question_set(
        role="frontend",
        interview_type=style,
        difficulty=difficulty,
        count=5,
        specialties=["React", "Unlisted specialty"],
    )
    assert len(questions) == 5
    assert "React" in questions[0]["text"]
    assert "Unlisted specialty" in questions[1]["text"]
    assert len({q["text"] for q in questions}) == 5
    if style == InterviewType.BEHAVIORAL:
        assert questions[0]["expected_concepts"] == ["situation", "task", "action", "result"]


async def test_adaptive_questions_keep_remaining_specialties(client, monkeypatch):
    from app.api.v1.answers import interview_graph

    owner = await _auth_headers(client)
    created = await client.post(
        "/api/v1/interviews",
        headers=owner,
        json={**SETUP, "specialties": ["React", "GraphQL", "Python"]},
    )
    session = created.json()
    monkeypatch.setattr(
        interview_graph,
        "ainvoke",
        AsyncMock(return_value={"action": "adjust_difficulty", "difficulty": "mid"}),
    )
    response = await client.post(
        f"/api/v1/questions/{session['questions'][0]['id']}/answer",
        headers=owner,
        json={
            "transcript": "State and props trigger a render; hooks manage state.",
            "duration_seconds": 20,
        },
    )
    assert response.status_code == 201
    saved = (await client.get(f"/api/v1/interviews/{session['id']}", headers=owner)).json()
    assert saved["difficulty"] == "mid"
    assert "GraphQL" in saved["questions"][1]["text"]
    assert "Python" in saved["questions"][2]["text"]
    assert "production failure modes" in saved["questions"][2]["text"]


async def test_llm_receives_selected_specialties(monkeypatch):
    from app.agents import llm_provider
    from app.schemas.question import QuestionBatch

    provider = AsyncMock()
    provider.generate_structured.return_value = QuestionBatch(
        questions=[
            {
                "text": "Explain GraphQL resolvers.",
                "expected_concepts": ["schema", "resolver", "query"],
                "follow_up_hint": None,
            }
        ]
    )
    monkeypatch.setattr(llm_provider, "get_llm_provider", lambda: provider)
    await QuestionService(None).generate_questions_with_llm(
        role="frontend",
        interview_type=InterviewType.TECHNICAL,
        difficulty=DifficultyLevel.JUNIOR,
        count=1,
        specialties=["GraphQL"],
    )
    assert '["GraphQL"]' in provider.generate_structured.call_args.args[0]
    assert "untrusted" in provider.generate_structured.call_args.kwargs["system"]


def test_local_schema_upgrade_preserves_existing_data():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE resumes (id CHAR(32) PRIMARY KEY)"))
        connection.execute(text("CREATE TABLE interviews (id CHAR(32) PRIMARY KEY, role TEXT)"))
        connection.execute(text("INSERT INTO interviews VALUES ('saved-session', 'frontend')"))
        upgrade_local_database(connection)
        upgrade_local_database(connection)
        row = connection.execute(text("SELECT * FROM interviews")).mappings().one()
        assert row["id"] == "saved-session"
        assert row["role"] == "frontend"
        assert row["resume_id"] is None
        assert row["specialties"] == "[]"
    engine.dispose()
