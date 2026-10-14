"""Regression coverage for ownership, security boundaries, and complete feature paths."""

import hashlib
import hmac
import importlib
import json
import pkgutil
import time
import uuid
from unittest.mock import AsyncMock

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from starlette.websockets import WebSocketDisconnect

import app
from app.core.config import Settings, settings
from app.core.exceptions import ServiceUnavailableError, ValidationAppError
from app.main import app as api
from app.models.interview import DifficultyLevel, InterviewRole, InterviewType
from app.models.memory import UserTopicPerformance
from app.models.user import RefreshToken, User
from app.services.question_service import QuestionService
from app.services.voice_service import VoiceService
from app.storage.s3_client import local_path
from tests.test_interviews import _auth_headers


async def make_interview(client, headers):
    response = await client.post(
        "/api/v1/interviews",
        headers=headers,
        json={
            "role": "backend",
            "interview_type": "technical",
            "difficulty": "junior",
            "question_count": 3,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def answer(client, headers, question, transcript="um I do not know"):
    return await client.post(
        f"/api/v1/questions/{question}/answer",
        headers=headers,
        json={"transcript": transcript, "duration_seconds": 10},
    )


def test_every_module_imports():
    for module in pkgutil.walk_packages(app.__path__, "app."):
        importlib.import_module(module.name)
    assert api.openapi()["paths"]["/api/v1/questions/{question_id}/answer"]


@pytest.mark.parametrize("role", list(InterviewRole))
@pytest.mark.parametrize("difficulty", list(DifficultyLevel))
def test_all_question_bank_roles(role, difficulty):
    seeds = QuestionService(None).build_question_set(
        role=role.value, interview_type=InterviewType.TECHNICAL, difficulty=difficulty, count=40
    )
    assert len(seeds) == 40
    assert all(item["text"] and item["expected_concepts"] for item in seeds)


async def test_google_requires_configuration(client, monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "")
    response = await client.post(
        "/api/v1/auth/google", json={"id_token": "forged.payload.signature"}
    )
    assert response.status_code == 503


async def test_google_verified_account_and_no_implicit_linking(client, monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "client-id")
    claims = {"email": "google@example.com", "email_verified": True, "sub": "verified-sub"}
    monkeypatch.setattr("google.oauth2.id_token.verify_oauth2_token", lambda *args: claims)
    result = await client.post("/api/v1/auth/google", json={"id_token": "valid-token"})
    assert result.status_code == 200
    claims["sub"] = "different-sub"
    result = await client.post("/api/v1/auth/google", json={"id_token": "valid-token"})
    assert result.status_code == 409
    claims["email_verified"] = False
    result = await client.post("/api/v1/auth/google", json={"id_token": "valid-token"})
    assert result.status_code == 401


async def test_refresh_is_hashed_logout_and_email_normalization(client, db_session):
    result = await client.post(
        "/api/v1/auth/register", json={"email": "User@Example.com", "password": "password123"}
    )
    token = result.json()["refresh_token"]
    stored = await db_session.scalar(select(RefreshToken))
    assert stored.token == hashlib.sha256(token.encode()).hexdigest()
    login = await client.post(
        "/api/v1/auth/login", json={"email": "user@example.com", "password": "password123"}
    )
    assert login.status_code == 200
    assert (
        await client.post("/api/v1/auth/logout", json={"refresh_token": token})
    ).status_code == 204
    assert (
        await client.post("/api/v1/auth/refresh", json={"refresh_token": token})
    ).status_code == 401


async def test_token_missing_expiry_rejected(client):
    token = jwt.encode(
        {"sub": str(uuid.uuid4()), "type": "access"}, settings.SECRET_KEY, algorithm="HS256"
    )
    assert (
        await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    ).status_code == 401


async def test_validation_does_not_echo_password(client):
    response = await client.post(
        "/api/v1/auth/register", json={"email": "invalid", "password": "secret"}
    )
    assert response.status_code == 422
    assert "secret" not in response.text


async def test_completion_rules_memory_and_late_answers(client, db_session):
    headers = await _auth_headers(client)
    interview = await make_interview(client, headers)
    endpoint = f"/api/v1/interviews/{interview['id']}/complete"
    assert (await client.post(endpoint, headers=headers)).status_code == 409
    follow_up = None
    for question in interview["questions"]:
        result = await answer(client, headers, question["id"])
        assert result.status_code == 201
        follow_up = result.json()["follow_up_question"]
    assert (await client.post(endpoint, headers=headers)).status_code == 200
    before = [
        (row.topic, row.attempts)
        for row in (await db_session.scalars(select(UserTopicPerformance))).all()
    ]
    assert before
    assert (await client.post(endpoint, headers=headers)).status_code == 200
    after = [
        (row.topic, row.attempts)
        for row in (await db_session.scalars(select(UserTopicPerformance))).all()
    ]
    assert before == after
    assert (await answer(client, headers, follow_up["id"])).status_code == 409


async def test_follow_up_is_bounded_and_ordered(client):
    headers = await _auth_headers(client)
    interview = await make_interview(client, headers)
    response = await answer(client, headers, interview["questions"][0]["id"])
    follow_up = response.json()["follow_up_question"]
    assert follow_up["order_index"] == 1
    second = await answer(client, headers, follow_up["id"])
    assert second.json()["follow_up_question"] is None
    details = await client.get(f"/api/v1/interviews/{interview['id']}", headers=headers)
    assert [q["order_index"] for q in details.json()["questions"]] == [0, 1, 2, 4]


async def test_answer_and_evaluation_owner_checks(client):
    owner = await _auth_headers(client)
    other = await _auth_headers(client, "other@example.com")
    interview = await make_interview(client, owner)
    qid = interview["questions"][0]["id"]
    assert (await answer(client, other, qid)).status_code == 403
    assert (
        await client.get(f"/api/v1/questions/{qid}/evaluation", headers=other)
    ).status_code == 403
    listed = await client.get("/api/v1/interviews", headers=other)
    assert listed.json() == []


async def test_dashboard_is_scoped_and_keeps_zero_fillers(client):
    owner = await _auth_headers(client)
    other = await _auth_headers(client, "other@example.com")
    interview = await make_interview(client, owner)
    await answer(client, owner, interview["questions"][0]["id"], "Clear speech without hesitation")
    a = (await client.get("/api/v1/dashboard", headers=owner)).json()
    b = (await client.get("/api/v1/dashboard", headers=other)).json()
    assert a["wpm_average"] > 0
    assert a["filler_word_rate"] == 0
    assert b["wpm_average"] == 0
    assert b["total_interviews"] == 0


async def test_resume_job_match_plan_report_and_download(client, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "LOCAL_STORAGE_DIR", str(tmp_path))
    headers = await _auth_headers(client)
    other = await _auth_headers(client, "other@example.com")
    upload = await client.post(
        "/api/v1/resumes/upload",
        headers=headers,
        files={
            "file": (
                "../../resume.txt",
                b"Python FastAPI Docker PostgreSQL experience",
                "text/plain",
            )
        },
    )
    assert upload.status_code == 201, upload.text
    resume = upload.json()
    assert resume["filename"] == "resume.txt"
    assert "Python" in resume["skills"]
    assert (await client.get(resume["file_url"], headers=headers)).status_code == 200
    assert (await client.get(resume["file_url"], headers=other)).status_code == 404
    assert (await client.get(f"/api/v1/resumes/{resume['id']}", headers=other)).status_code == 404
    job = await client.post(
        "/api/v1/jobs",
        headers=headers,
        json={
            "title": "Backend developer",
            "raw_text": "Python FastAPI Docker PostgreSQL and Kubernetes required",
        },
    )
    assert job.status_code == 201
    match = await client.post(
        "/api/v1/matching",
        headers=headers,
        json={"resume_id": resume["id"], "job_id": job.json()["id"]},
    )
    assert match.status_code == 200, match.text
    assert "Kubernetes" in match.json()["missing_skills"]
    plan = await client.post(
        "/api/v1/learning-plans",
        headers=headers,
        json={"duration_days": 14, "focus_topics": ["Python"]},
    )
    assert plan.status_code == 201, plan.text
    assert plan.json()["focus_topics"] == ["Python"]
    assert (
        await client.get(f"/api/v1/learning-plans/{plan.json()['id']}", headers=other)
    ).status_code == 404
    interview = await make_interview(client, headers)
    report = await client.post(
        "/api/v1/reports/generate", headers=headers, json={"interview_id": interview["id"]}
    )
    assert report.status_code == 201, report.text
    pdf = await client.get(report.json()["download_url"], headers=headers)
    assert pdf.content.startswith(b"%PDF")
    import fitz

    with fitz.open(stream=pdf.content, filetype="pdf") as document:
        assert "Interview Performance Report" in document[0].get_text()


@pytest.mark.parametrize(
    "name,data", [("invalid.pdf", b"not a PDF"), ("old.doc", b"binary"), ("empty.txt", b"")]
)
async def test_invalid_uploads_rejected(client, name, data):
    headers = await _auth_headers(client)
    response = await client.post(
        "/api/v1/resumes/upload", headers=headers, files={"file": (name, data)}
    )
    assert response.status_code in {400, 422}


async def test_upload_and_body_limits(client, monkeypatch):
    headers = await _auth_headers(client)
    monkeypatch.setattr(settings, "MAX_UPLOAD_BYTES", 1024)
    response = await client.post(
        "/api/v1/resumes/upload", headers=headers, files={"file": ("big.txt", b"a" * 1025)}
    )
    assert response.status_code == 422
    response = await client.post("/api/v1/auth/login", content=b"a" * (1024 * 1024 + 1))
    assert response.status_code == 413


@pytest.mark.parametrize("key", ["../secret", "resumes/../../secret", "C:/secret", "\\secret"])
def test_storage_rejects_unsafe_paths(key):
    with pytest.raises(ValidationAppError):
        local_path(key)


async def test_knowledge_ingestion_idempotent_and_search(client, db_session):
    from app.agents.rag.ingest import ingest_seed_documents

    assert await ingest_seed_documents(db_session) == 4
    assert await ingest_seed_documents(db_session) == 0
    headers = await _auth_headers(client)
    result = await client.get("/api/v1/knowledge-base/search?query=PostgreSQL", headers=headers)
    assert result.status_code == 200 and result.json()
    qa = await client.post(
        "/api/v1/knowledge-base/qa", headers=headers, json={"query": "PostgreSQL"}
    )
    assert qa.status_code == 200 and qa.json()["sources"]


async def test_unconfigured_speech_and_billing_fail_honestly(client, monkeypatch):
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "")
    with pytest.raises(ServiceUnavailableError):
        await VoiceService.transcribe_audio_bytes(b"audio")
    with pytest.raises(ServiceUnavailableError):
        await VoiceService.synthesize_speech("Hello")
    headers = await _auth_headers(client)
    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "")
    monkeypatch.setattr(settings, "STRIPE_PRICE_ID_PRO", "")
    assert (
        await client.post("/api/v1/subscriptions/checkout-session", headers=headers, json={})
    ).status_code == 503


async def test_webhook_requires_signature_and_deduplicates(client, monkeypatch, db_session):
    from app.models.subscription import WebhookEvent

    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", "whsec_test")
    assert (
        await client.post("/api/v1/webhooks/stripe", json={"type": "checkout.session.completed"})
    ).status_code == 422
    event = {"id": "evt_test", "type": "unhandled.event", "data": {"object": {}}}
    body = json.dumps(event).encode()
    timestamp = int(time.time())
    signature = hmac.new(
        b"whsec_test", str(timestamp).encode() + b"." + body, hashlib.sha256
    ).hexdigest()
    headers = {"stripe-signature": f"t={timestamp},v1={signature}"}
    for _ in range(2):
        assert (
            await client.post("/api/v1/webhooks/stripe", content=body, headers=headers)
        ).status_code == 200
    assert len((await db_session.scalars(select(WebhookEvent))).all()) == 1
    assert (
        await client.post("/api/v1/webhooks/stripe", content=body + b"x", headers=headers)
    ).status_code == 422


async def test_subscription_lifecycle_updates_actual_user_plan(client, db_session, monkeypatch):
    from app.models.user import SubscriptionPlan
    from app.services.subscription_service import SubscriptionService

    await _auth_headers(client)
    user = await db_session.scalar(select(User))
    current = {
        "id": "sub_test",
        "customer": "cus_test",
        "created": 100,
        "metadata": {"user_id": str(user.id)},
        "status": "active",
        "items": {"data": [{"price": {"id": "price_pro"}, "current_period_end": 2000000000}]},
    }
    monkeypatch.setattr(settings, "STRIPE_PRICE_ID_PRO", "price_pro")
    monkeypatch.setattr(
        "app.services.subscription_service.stripe_call", AsyncMock(return_value=current)
    )
    for index, state in enumerate(["active", "past_due", "canceled"]):
        current["status"] = state
        await SubscriptionService.handle_event(
            {
                "id": f"evt_{index}",
                "type": "customer.subscription.updated",
                "data": {"object": {"id": "sub_test"}},
            },
            db_session,
        )
        await db_session.refresh(user)
        assert user.plan == (SubscriptionPlan.PRO if state == "active" else SubscriptionPlan.FREE)


async def test_rate_limiter_fails_closed_and_limits(client, monkeypatch):
    from redis.exceptions import ConnectionError

    from app.core.exceptions import RateLimitedError
    from app.core.rate_limit import check_rate_limit

    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
    pool = AsyncMock()
    monkeypatch.setattr("app.core.rate_limit.get_redis_pool", lambda: pool)
    pool.eval.return_value = 11
    with pytest.raises(RateLimitedError):
        await check_rate_limit("identity", 10)
    pool.eval.side_effect = ConnectionError("unavailable")
    assert (await client.post("/api/v1/auth/login", json={})).status_code == 503
    assert (await client.get("/health")).status_code == 200


def test_websocket_requires_origin_and_authentication():
    with TestClient(api, base_url="http://test") as client:
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(
                f"ws://test/api/v1/voice/ws/{uuid.uuid4()}",
                headers={"Origin": "https://evil.example"},
            ):
                pytest.fail("Foreign origin accepted")
        with client.websocket_connect(f"ws://test/api/v1/voice/ws/{uuid.uuid4()}") as socket:
            socket.send_json({"access_token": "forged"})
            assert socket.receive_json()["error"]["code"] == "unauthorized"


def test_production_settings_reject_insecure_defaults():
    with pytest.raises(ValueError):
        Settings(
            _env_file=None,
            APP_ENV="production",
            DEBUG=True,
            SECRET_KEY="weak",
            DATABASE_URL="sqlite+aiosqlite:///:memory:",
        )


async def test_ai_failures_rollback_interview_creation(client, monkeypatch):
    headers = await _auth_headers(client)
    monkeypatch.setattr(settings, "AI_ENABLED", True)
    monkeypatch.setattr(
        "app.services.question_service.QuestionService.generate_questions_with_llm",
        AsyncMock(side_effect=ServiceUnavailableError("Provider unavailable")),
    )
    response = await client.post(
        "/api/v1/interviews",
        headers=headers,
        json={
            "role": "backend",
            "interview_type": "technical",
            "difficulty": "junior",
            "question_count": 3,
        },
    )
    assert response.status_code == 503
    assert (await client.get("/api/v1/interviews", headers=headers)).json() == []


async def test_voice_authentication_and_owner_check(client, db_session, monkeypatch):
    owner = await _auth_headers(client)
    other = await _auth_headers(client, "voice-other@example.com")
    interview = await make_interview(client, owner)
    monkeypatch.setattr(
        VoiceService, "transcribe_audio_bytes", AsyncMock(return_value="real transcript")
    )
    endpoint = f"ws://test/api/v1/voice/ws/{interview['questions'][0]['id']}"
    with TestClient(api, base_url="http://test") as sync:
        with sync.websocket_connect(endpoint) as socket:
            socket.send_json({"access_token": other["Authorization"].split()[1]})
            assert socket.receive_json()["error"]["code"] == "forbidden"
        with sync.websocket_connect(endpoint) as socket:
            socket.send_json({"access_token": owner["Authorization"].split()[1]})
            assert socket.receive_json()["authenticated"]
            socket.send_bytes(b"sample audio")
            assert socket.receive_json()["transcript"] == "real transcript"


async def test_n8n_signed_callback(client, monkeypatch):
    monkeypatch.setattr(settings, "N8N_WEBHOOK_SECRET", "automation-test-secret")
    body = b'{"status":"done"}'
    stamp = str(int(time.time()))
    signature = hmac.new(
        b"automation-test-secret", stamp.encode() + b"." + body, hashlib.sha256
    ).hexdigest()
    headers = {"x-webhook-timestamp": stamp, "x-webhook-signature": signature}
    assert (
        await client.post("/api/v1/webhooks/n8n", content=body, headers=headers)
    ).status_code == 200
    assert (
        await client.post("/api/v1/webhooks/n8n", content=b"altered", headers=headers)
    ).status_code == 401
    headers["x-webhook-timestamp"] = "0"
    assert (
        await client.post("/api/v1/webhooks/n8n", content=body, headers=headers)
    ).status_code == 401


async def test_inactive_user_cannot_login_refresh_or_access(client, db_session):
    registered = await client.post(
        "/api/v1/auth/register",
        json={"email": "inactive@example.com", "password": "secret-password"},
    )
    tokens = registered.json()
    user = await db_session.scalar(select(User))
    user.is_active = False
    await db_session.commit()
    assert (
        await client.post(
            "/api/v1/auth/login", json={"email": user.email, "password": "secret-password"}
        )
    ).status_code == 401
    assert (
        await client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    ).status_code == 401
    assert (
        await client.get(
            "/api/v1/users/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )
    ).status_code == 401


async def test_storage_failure_never_falls_back_to_disk(monkeypatch, tmp_path):
    from unittest.mock import Mock

    from botocore.exceptions import EndpointConnectionError

    from app.storage.s3_client import upload_file

    monkeypatch.setattr(settings, "STORAGE_BACKEND", "s3")
    monkeypatch.setattr(settings, "LOCAL_STORAGE_DIR", str(tmp_path))
    cloud = Mock()
    cloud.put_object.side_effect = EndpointConnectionError(endpoint_url="https://storage.invalid")
    monkeypatch.setattr("app.storage.s3_client._get_boto3_client", lambda: cloud)
    with pytest.raises(ServiceUnavailableError):
        upload_file("resumes/user/sample.txt", b"sensitive")
    assert list(tmp_path.iterdir()) == []
