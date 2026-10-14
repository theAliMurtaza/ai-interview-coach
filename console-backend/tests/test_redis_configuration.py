"""Catch hosted Redis URL mistakes without leaking credentials or hiding readiness."""

from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from app.core.config import settings
from app.core.redis import get_redis_pool
from tests.test_deployment import production_settings


@pytest.mark.parametrize(
    "url",
    [
        "https://default:private-password@example.upstash.io",
        "redis-cli --tls -u redis://default:private-password@example.upstash.io:6379",
        "rediss://",
        "rediss://default:private-password@example.upstash.io:bad",
        "rediss://example.upstash.io:0",
        "rediss://example.upstash.io/not-a-db",
        " rediss://example.upstash.io",
        "rediss://example.upstash.io\n",
    ],
)
def test_invalid_redis_urls_are_rejected_without_printing_secrets(url):
    with pytest.raises(ValidationError) as error:
        production_settings(REDIS_URL=url)
    assert "REDIS_URL must be a Redis connection URL" in str(error.value)
    assert "private-password" not in str(error.value)
    assert "918e349e5a7c123df86537ba269c04ae298736ab429572ac" not in str(error.value)


@pytest.mark.parametrize(
    "url",
    [
        "rediss://default:p%40ss%25word@example.upstash.io:6379",
        "redis://localhost:6379/0",
        "rediss://example.upstash.io",
    ],
)
def test_valid_redis_urls_are_preserved(url):
    assert production_settings(REDIS_URL=url).REDIS_URL == url


async def test_redis_configuration_error_is_503_but_liveness_and_root_work(client, monkeypatch):
    # Reproduce a malformed setting from older deployments, bypassing startup validation.
    monkeypatch.setattr(
        settings, "REDIS_URL", "https://default:private-password@example.upstash.io"
    )
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
    get_redis_pool.cache_clear()
    try:
        assert (await client.get("/health")).status_code == 200
        root = await client.get("/")
        assert root.status_code == 200
        assert root.json()["readiness"] == "/ready"
        for path in ("/ready", "/api/v1/users/me"):
            response = await client.get(path)
            assert response.status_code == 503
            assert response.json()["error"]["code"] == "service_unavailable"
            assert "REDIS_URL" in response.json()["error"]["message"]
            assert "private-password" not in response.text
    finally:
        get_redis_pool.cache_clear()


async def test_readiness_checks_database_and_redis(client, monkeypatch):
    pool = AsyncMock()
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr("app.main.get_redis_pool", lambda: pool)
    response = await client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}
    pool.ping.assert_awaited_once()
