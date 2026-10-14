import pytest
from httpx import AsyncClient


async def _auth_headers(client: AsyncClient, email: str = "interviewee@example.com") -> dict:
    register = await client.post(
        "/api/v1/auth/register", json={"email": email, "password": "supersecret123"}
    )
    token = register.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_create_interview_returns_requested_question_count(client: AsyncClient) -> None:
    headers = await _auth_headers(client)
    response = await client.post(
        "/api/v1/interviews",
        headers=headers,
        json={
            "role": "backend",
            "interview_type": "technical",
            "difficulty": "junior",
            "question_count": 5,
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert len(body["questions"]) == 5
    assert body["status"] == "in_progress"


@pytest.mark.asyncio
async def test_create_interview_caps_question_count_at_40(client: AsyncClient) -> None:
    headers = await _auth_headers(client)
    response = await client.post(
        "/api/v1/interviews",
        headers=headers,
        json={
            "role": "backend",
            "interview_type": "behavioral",
            "difficulty": "junior",
            "question_count": 999,
        },
    )
    # Pydantic's Field(le=40) on InterviewCreate rejects this before it
    # ever reaches build_question_set's own internal cap.
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_interview_rejects_other_users_data(client: AsyncClient) -> None:
    owner_headers = await _auth_headers(client, "owner@example.com")
    other_headers = await _auth_headers(client, "other@example.com")

    created = await client.post(
        "/api/v1/interviews",
        headers=owner_headers,
        json={
            "role": "frontend",
            "interview_type": "technical",
            "difficulty": "junior",
            "question_count": 3,
        },
    )
    interview_id = created.json()["id"]

    response = await client.get(f"/api/v1/interviews/{interview_id}", headers=other_headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_weak_answer_triggers_follow_up(client: AsyncClient) -> None:
    headers = await _auth_headers(client, "weakanswer@example.com")
    created = await client.post(
        "/api/v1/interviews",
        headers=headers,
        json={
            "role": "frontend",
            "interview_type": "technical",
            "difficulty": "junior",
            "question_count": 3,
        },
    )
    question_id = created.json()["questions"][0]["id"]

    response = await client.post(
        f"/api/v1/questions/{question_id}/answer",
        headers=headers,
        json={"transcript": "um uh I dont know", "duration_seconds": 3},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["evaluation"]["overall_score"] < 55
    assert body["follow_up_question"] is not None


@pytest.mark.asyncio
async def test_cannot_answer_the_same_question_twice(client: AsyncClient) -> None:
    headers = await _auth_headers(client, "doubleanswer@example.com")
    created = await client.post(
        "/api/v1/interviews",
        headers=headers,
        json={
            "role": "frontend",
            "interview_type": "technical",
            "difficulty": "junior",
            "question_count": 3,
        },
    )
    question_id = created.json()["questions"][0]["id"]

    first = await client.post(
        f"/api/v1/questions/{question_id}/answer",
        headers=headers,
        json={"transcript": "a reasonably detailed answer here", "duration_seconds": 8},
    )
    assert first.status_code == 201

    second = await client.post(
        f"/api/v1/questions/{question_id}/answer",
        headers=headers,
        json={"transcript": "trying again", "duration_seconds": 3},
    )
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_complete_interview_rolls_up_scores(client: AsyncClient) -> None:
    headers = await _auth_headers(client, "complete@example.com")
    created = await client.post(
        "/api/v1/interviews",
        headers=headers,
        json={
            "role": "backend",
            "interview_type": "technical",
            "difficulty": "junior",
            "question_count": 3,
        },
    )
    interview = created.json()
    for q in interview["questions"]:
        await client.post(
            f"/api/v1/questions/{q['id']}/answer",
            headers=headers,
            json={
                "transcript": "A clear, detailed answer covering the relevant concepts.",
                "duration_seconds": 10,
            },
        )

    response = await client.post(f"/api/v1/interviews/{interview['id']}/complete", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["overall_score"] is not None
