import runpy
import uuid
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from pydantic import ValidationError
from sqlalchemy import create_engine, text

from app.core.config import settings
from app.core.local_migrations import upgrade_local_database
from app.models.interview import DifficultyLevel, InterviewType
from app.models.resume import Resume
from app.schemas.evaluation import AIGrade
from app.services.evaluation_service import EvaluationService
from app.services.question_service import QuestionService
from app.services.resume_projects import resume_projects
from tests.test_interviews import _auth_headers

RESUME = """Alex Candidate
Backend Developer
Skills: Python, FastAPI, React
Projects
Interview Coach | Python, FastAPI
• Built interview sessions with private resume uploads.
• Implemented token authentication and tested API endpoints.
Shop Portal: React and PostgreSQL
Developed product search and order tracking.
Education
University of Example
"""
SETUP = {
    "role": "backend",
    "interview_type": "technical",
    "difficulty": "junior",
    "question_count": 3,
}


def test_projects_are_named_bounded_and_do_not_include_experience_or_education():
    projects = resume_projects(RESUME)
    assert [p["name"] for p in projects] == ["Interview Coach", "Shop Portal"]
    assert projects[0]["technologies"] == ["Python", "FastAPI"]
    assert "private resume uploads" in projects[0]["description"]
    assert (
        resume_projects("Experience\nBuilt Interview Coach using Python\nEducation\nCollege") == []
    )
    assert resume_projects(RESUME, [{"name": "Invented Project"}]) == projects


def test_project_titles_are_not_confused_with_section_names():
    projects = resume_projects(
        "Projects\nProject 1: Education Portal\nBuilt with Python.\n"
        "• Skills Tracker | React\nDeveloped a dashboard.\nSkills: Python, React"
    )
    assert [p["name"] for p in projects] == ["Education Portal", "Skills Tracker"]


@pytest.mark.parametrize("style", list(InterviewType))
def test_project_questions_keep_names_and_style(style):
    questions = QuestionService(None).build_question_set(
        role="backend",
        interview_type=style,
        difficulty=DifficultyLevel.JUNIOR,
        count=3,
        projects=resume_projects(RESUME),
        specialties=["Python"],
    )
    assert len(questions) == 3
    assert '"Interview Coach"' in questions[0]["text"]
    assert '"Shop Portal"' in questions[2]["text"]
    assert "Python" in questions[1]["text"]
    if style == InterviewType.BEHAVIORAL:
        assert "personal responsibility" in questions[0]["text"]


async def test_saved_resume_projects_survive_adaptation_and_remain_private(
    client, db_session, monkeypatch, tmp_path
):
    monkeypatch.setattr(settings, "LOCAL_STORAGE_DIR", str(tmp_path))
    owner = await _auth_headers(client)
    uploaded = await client.post(
        "/api/v1/resumes/upload",
        headers=owner,
        files={
            "file": ("resume.txt", RESUME.encode(), "text/plain"),
        },
    )
    resume = uploaded.json()
    assert len(resume["projects"]) == 2
    # Older resumes have raw text but no parsed projects; reuse still detects them.
    saved_resume = await db_session.get(Resume, uuid.UUID(resume["id"]))
    saved_resume.projects = []
    await db_session.commit()
    listed = (await client.get("/api/v1/resumes", headers=owner)).json()
    assert len(listed[0]["projects"]) == 2
    created = await client.post(
        "/api/v1/interviews", headers=owner, json={**SETUP, "resume_id": resume["id"]}
    )
    assert created.status_code == 201
    session = created.json()
    assert "Interview Coach" in session["questions"][0]["text"]
    # Project context was snapshotted; later resume edits cannot change the session.
    saved_resume.raw_text = "No projects"
    await db_session.commit()
    from app.api.v1.answers import interview_graph

    monkeypatch.setattr(
        interview_graph,
        "ainvoke",
        AsyncMock(
            return_value={
                "action": "adjust_difficulty",
                "difficulty": "mid",
            }
        ),
    )
    submitted = await client.post(
        f"/api/v1/questions/{session['questions'][0]['id']}/answer",
        headers=owner,
        json={
            "transcript": "The problem was solved. I implemented a test and measured the result.",
            "duration_seconds": 10,
        },
    )
    assert submitted.status_code == 201
    assessment = submitted.json()["evaluation"]["assessment"]
    assert assessment["method"] == "keyword"
    assert assessment["correct_percentage"] is None
    assert assessment["improvements"]
    reloaded = (await client.get(f"/api/v1/interviews/{session['id']}", headers=owner)).json()
    assert "Shop Portal" in reloaded["questions"][2]["text"]
    assert "architecture" in reloaded["questions"][2]["text"]
    assert reloaded["questions"][0]["answer"]["evaluation"]["assessment"] == assessment
    other = await _auth_headers(client, "projects-other@example.com")
    denied = await client.post(
        "/api/v1/interviews", headers=other, json={**SETUP, "resume_id": resume["id"]}
    )
    assert denied.status_code == 404


def test_keyword_coverage_does_not_claim_factual_accuracy_and_silence_is_missing():
    evaluator = EvaluationService()
    result = evaluator.evaluate(
        transcript="Python always uses no memory",
        duration_seconds=10,
        expected_concepts=["Python", "iterator"],
    )
    assert result.assessment.coverage_percentage == 50
    assert result.assessment.missing_percentage == 50
    assert result.assessment.correct_percentage is None
    assert result.assessment.incorrect_percentage is None
    assert "iterator" in result.assessment.improvements[0]
    skipped = evaluator.evaluate(transcript="", duration_seconds=1, expected_concepts=["Python"])
    assert skipped.assessment.correct_percentage == 0
    assert skipped.assessment.incorrect_percentage == 0
    assert skipped.assessment.missing_percentage == 100


def grade_data():
    return dict(
        technical_score=60,
        feedback="Correct the claim about memory, then explain iterators.",
        correct_percentage=60,
        incorrect_percentage=20,
        missing_percentage=20,
        strengths=["Identifies Python as the implementation language."],
        corrections=["Python allocates memory; generators avoid retaining all results."],
        improvements=["Show a generator example and compare its memory use to a list."],
    )


@pytest.mark.parametrize(
    "update",
    [
        {"correct_percentage": 101},
        {"incorrect_percentage": -1},
        {"missing_percentage": 50},
        {"correct_percentage": float("nan")},
        {"corrections": []},
        {"improvements": []},
    ],
)
def test_invalid_ai_assessments_are_rejected(update):
    with pytest.raises(ValidationError):
        AIGrade(**{**grade_data(), **update})


async def test_ai_assessment_persists_and_project_context_reaches_provider(client, monkeypatch):
    from app.agents import llm_provider
    from app.schemas.question import QuestionBatch

    owner = await _auth_headers(client)
    session = (await client.post("/api/v1/interviews", headers=owner, json=SETUP)).json()
    provider = AsyncMock()
    provider.generate_structured.return_value = AIGrade(**grade_data())
    monkeypatch.setattr(llm_provider, "get_llm_provider", lambda: provider)
    monkeypatch.setattr(settings, "AI_ENABLED", True)
    result = await client.post(
        f"/api/v1/questions/{session['questions'][0]['id']}/answer",
        headers=owner,
        json={"transcript": "Python uses no memory", "duration_seconds": 10},
    )
    assert result.status_code == 201
    data = result.json()["evaluation"]["assessment"]
    assert data["method"] == "ai"
    assert data["incorrect_percentage"] == 20
    assert data["corrections"] == grade_data()["corrections"]
    saved = (await client.get(f"/api/v1/interviews/{session['id']}", headers=owner)).json()
    assert saved["questions"][0]["answer"]["evaluation"]["assessment"] == data
    provider.generate_structured.return_value = QuestionBatch(
        questions=[
            {
                "text": "Explain Python",
                "expected_concepts": ["Python"],
                "follow_up_hint": None,
            }
        ]
    )
    questions = await QuestionService(None).generate_questions_with_llm(
        role="backend",
        interview_type=InterviewType.TECHNICAL,
        difficulty=DifficultyLevel.JUNIOR,
        count=1,
        projects=resume_projects(RESUME),
    )
    assert "private resume uploads" in provider.generate_structured.call_args.args[0]
    assert "Interview Coach" in questions[0]["text"]


def test_additive_schema_upgrade_keeps_old_scores_and_handles_restarts():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE interviews (id TEXT, specialties JSON, resume_id TEXT)"))
        conn.execute(text("CREATE TABLE evaluations (id TEXT, overall_score FLOAT)"))
        conn.execute(text("INSERT INTO interviews VALUES ('saved', '[]', NULL)"))
        conn.execute(text("INSERT INTO evaluations VALUES ('old', 75)"))
        upgrade_local_database(conn)
        upgrade_local_database(conn)
        assert conn.execute(text("SELECT resume_projects FROM interviews")).scalar() == "[]"
        row = conn.execute(text("SELECT overall_score, assessment FROM evaluations")).one()
        assert row == (75, "{}")
    engine.dispose()


def test_release_migration_preserves_rows_and_downgrades_only_new_columns():
    revision = runpy.run_path(
        str(
            Path(__file__).resolve().parents[1] / "alembic/versions/0004_projects_and_assessment.py"
        )
    )
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE interviews (id TEXT)"))
        conn.execute(text("CREATE TABLE evaluations (id TEXT, overall_score FLOAT)"))
        conn.execute(text("INSERT INTO interviews VALUES ('saved')"))
        conn.execute(text("INSERT INTO evaluations VALUES ('old', 75)"))
        with Operations.context(MigrationContext.configure(conn)):
            revision["upgrade"]()
            assert conn.execute(text("SELECT resume_projects FROM interviews")).scalar() == "[]"
            assert conn.execute(text("SELECT assessment FROM evaluations")).scalar() == "{}"
            revision["downgrade"]()
        assert conn.execute(text("SELECT id FROM interviews")).scalar() == "saved"
        assert conn.execute(text("SELECT overall_score FROM evaluations")).scalar() == 75
    engine.dispose()
