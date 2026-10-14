"""Shared Redis connection for request limits and short-lived private caches."""

import logging
from functools import lru_cache

import redis.asyncio as redis

from app.core.config import settings
from app.core.exceptions import ServiceUnavailableError


@lru_cache
def get_redis_pool() -> redis.Redis:
    try:
        return redis.from_url(
            settings.REDIS_URL, decode_responses=True, socket_connect_timeout=2, socket_timeout=2
        )
    except (ValueError, TypeError):
        # Never log the supplied URL: it contains the Redis password.
        logging.getLogger(__name__).error("Invalid Redis client configuration; check REDIS_URL")
        raise ServiceUnavailableError("Redis configuration is invalid; check REDIS_URL") from None
