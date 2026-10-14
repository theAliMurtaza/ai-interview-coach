"""API contracts required for saved reports and safe interview resumption."""

from app.core.config import settings
from tests.test_interviews import _auth_headers


async def test_saved_answers_and_evaluations_are_owner_scoped(client, monkeypatch):
    owner = await _auth_headers(client, "owner-contract@example.com")
    other = await _auth_headers(client, "other-contract@example.com")
    created = await client.post(
        "/api/v1/interviews",
        headers=owner,
        json={
            "role": "frontend",
            "interview_type": "technical",
            "difficulty": "junior",
            "question_count": 3,
        },
    )
    assert created.status_code == 201
    interview = created.json()
    assert all(q["answer"] is None for q in interview["questions"])
    monkeypatch.setattr(settings, "AI_ENABLED", True)
    for question in interview["questions"]:
        response = await client.post(
            f"/api/v1/questions/{question['id']}/answer",
            headers=owner,
            json={"transcript": "", "duration_seconds": 1},
        )
        assert response.status_code == 201
        assert response.json()["follow_up_question"] is None
    completed = await client.post(f"/api/v1/interviews/{interview['id']}/complete", headers=owner)
    assert completed.status_code == 200
    saved = (await client.get(f"/api/v1/interviews/{interview['id']}", headers=owner)).json()
    assert saved["status"] == "completed"
    assert len(saved["questions"]) == 3
    assert saved["questions"][0]["answer"]["evaluation"]["overall_score"] == 0
    assert saved["questions"][0]["answer"]["duration_seconds"] == 1
    assert (
        await client.get(f"/api/v1/interviews/{interview['id']}", headers=other)
    ).status_code == 403
