"""Opt-in Redis integration without touching other keys."""

import hashlib
import os
import uuid

import pytest
import redis.asyncio as redis

from app.core.config import settings
from app.core.exceptions import RateLimitedError
from app.core.rate_limit import check_rate_limit


@pytest.mark.skipif(not os.environ.get("TEST_REDIS_URL"), reason="Set TEST_REDIS_URL")
async def test_real_redis_rate_limit(monkeypatch):
    pool = redis.from_url(os.environ["TEST_REDIS_URL"], decode_responses=True)
    identity = "integration-test:" + str(uuid.uuid4())
    key = "rate:" + hashlib.sha256(identity.encode()).hexdigest()
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr("app.core.rate_limit.get_redis_pool", lambda: pool)
    try:
        await check_rate_limit(identity, 2)
        await check_rate_limit(identity, 2)
        with pytest.raises(RateLimitedError):
            await check_rate_limit(identity, 2)
        assert 0 < await pool.ttl(key) <= 60
    finally:
        await pool.delete(key)
        await pool.aclose()
