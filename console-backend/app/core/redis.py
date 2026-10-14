"""Shared Redis connection for request limits and short-lived private caches."""

from functools import lru_cache

import redis.asyncio as redis

from app.core.config import settings


@lru_cache
def get_redis_pool() -> redis.Redis:
    return redis.from_url(
        settings.REDIS_URL, decode_responses=True, socket_connect_timeout=2, socket_timeout=2
    )
