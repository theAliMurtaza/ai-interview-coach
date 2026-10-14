"""Atomic Redis fixed-window limits shared across API workers."""

import hashlib

from redis.exceptions import RedisError

from app.core.config import settings
from app.core.exceptions import RateLimitedError, ServiceUnavailableError
from app.core.redis import get_redis_pool

_SCRIPT = """
local n = redis.call('INCR', KEYS[1])
if n == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
return n
"""


async def check_rate_limit(identity: str, limit: int) -> None:
    if not settings.RATE_LIMIT_ENABLED:
        return
    key = "rate:" + hashlib.sha256(identity.encode()).hexdigest()
    try:
        count = await get_redis_pool().eval(_SCRIPT, 1, key, 60)
    except RedisError as exc:
        raise ServiceUnavailableError("Request limiter is unavailable") from exc
    if int(count) > limit:
        raise RateLimitedError("Too many requests; try again in one minute")
