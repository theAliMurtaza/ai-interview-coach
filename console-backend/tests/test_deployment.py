"""Regressions for deployment guards and request admission."""

from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from app.core.config import Settings, settings
from app.core.exceptions import ValidationAppError
from app.models.user import SubscriptionPlan, User
from app.services.evaluation_service import EvaluationService
from app.services.subscription_service import SubscriptionService
from app.storage.s3_client import validate_key
from tests.test_interviews import _auth_headers


def production_settings(**overrides):
    values = dict(
        APP_ENV="production",
        SECRET_KEY="918e349e5a7c123df86537ba269c04ae298736ab429572ac",
        DATABASE_URL="postgresql+asyncpg://user:password@db/app",
        RATE_LIMIT_ENABLED=True,
        STORAGE_BACKEND="s3",
        ALLOWED_HOSTS=["api.example.org"],
        BACKEND_CORS_ORIGINS=["https://app.example.org"],
    )
    return Settings(_env_file=None, **(values | overrides))


@pytest.mark.parametrize("secret", ["replace-with-a-generated-random-secret", "x" * 64])
def test_production_rejects_placeholder_secrets(secret):
    with pytest.raises(ValueError):
        production_settings(SECRET_KEY=secret)


@pytest.mark.parametrize(
    "origin",
    [
        "https://",
        "https://*.example.org",
        "https://app.example.org/path",
        "https://user:pass@app.example.org",
        "https://app.example.org/",
    ],
)
def test_production_requires_valid_origins(origin):
    with pytest.raises(ValueError):
        production_settings(BACKEND_CORS_ORIGINS=[origin])


def test_valid_production_configuration():
    assert production_settings().APP_ENV == "production"


def test_concept_matching_does_not_reward_unrelated_substrings():
    result = EvaluationService().evaluate(
        transcript="My reaction followed principles",
        duration_seconds=5,
        expected_concepts=["react", "ci"],
    )
    assert result.concepts_hit == []


def test_ai_must_have_provider_credentials():
    with pytest.raises(ValueError):
        production_settings(AI_ENABLED=True, OPENAI_API_KEY="", LLM_PROVIDER="openai")


@pytest.mark.parametrize("key", ["resumes/user/\x00.txt", "reports/user/\n.pdf"])
def test_storage_rejects_control_characters(key):
    with pytest.raises(ValidationAppError):
        validate_key(key)


async def test_webhooks_have_separate_rate_limit(client, monkeypatch):
    limiter = AsyncMock()
    monkeypatch.setattr("app.core.middleware.check_rate_limit", limiter)
    await client.post("/api/v1/webhooks/stripe", content=b"invalid")
    limiter.assert_awaited_once_with("webhook:127.0.0.1", settings.WEBHOOK_RATE_LIMIT_PER_MINUTE)


async def test_billing_reloads_current_state_after_owner_lock(client, db_session, monkeypatch):
    await _auth_headers(client)
    user = await db_session.scalar(select(User))
    base = {
        "metadata": {"user_id": str(user.id)},
        "created": 100,
        "customer": "cus_test",
        "items": {"data": [{"price": {"id": "price_pro"}}]},
    }
    provider = AsyncMock(side_effect=[base | {"status": "active"}, base | {"status": "canceled"}])
    monkeypatch.setattr("app.services.subscription_service.stripe_call", provider)
    monkeypatch.setattr(settings, "STRIPE_PRICE_ID_PRO", "price_pro")
    await SubscriptionService.handle_event(
        {
            "id": "evt_race",
            "type": "customer.subscription.updated",
            "data": {"object": {"id": "sub_test"}},
        },
        db_session,
    )
    await db_session.refresh(user)
    assert user.plan == SubscriptionPlan.FREE
    assert provider.await_count == 2
