"""In-process sliding-window rate limiter.

Per-process state is sufficient for a single backend instance; a Redis-backed
limiter can replace this without changing the middleware contract.
"""

import time
import uuid
from collections import defaultdict, deque
from typing import Dict, Tuple


class RateLimiter:
    def __init__(self, default_limit: int = 120):
        self.default_limit = default_limit
        self._events: Dict[str, deque] = defaultdict(deque)  # type: ignore[type-arg]

    def check(self, key: str, limit: int | None = None) -> Tuple[bool, int]:
        """Return (allowed, retry_after_seconds)."""
        limit = limit or self.default_limit
        now = time.monotonic()
        window = self._events[key]
        while window and window[0] <= now - 60:
            window.popleft()
        if len(window) >= limit:
            return False, max(1, int(60 - (now - window[0])) + 1)
        window.append(now)
        return True, 0

    def reset(self, key: str | None = None) -> None:
        if key is None:
            self._events.clear()
        else:
            self._events.pop(key, None)


class RedisRateLimiter:
    """Shared sliding window across backend replicas."""

    def __init__(self, url: str, default_limit: int = 120):
        self.url = url
        self.default_limit = default_limit

    async def check(self, key: str, limit: int | None = None) -> Tuple[bool, int]:
        import redis.asyncio as redis

        limit = limit or self.default_limit
        client = redis.from_url(self.url, decode_responses=True)  # type: ignore[no-untyped-call]
        now = time.time()
        member = f"{now}-{uuid.uuid4().hex}"
        try:
            pipe = client.pipeline()
            pipe.zremrangebyscore(key, 0, now - 60)
            pipe.zcard(key)
            pipe.zadd(key, {member: now})
            pipe.expire(key, 60)
            results = await pipe.execute()
            prior_count = int(results[1])
            if prior_count >= limit:
                oldest = await client.zrange(key, 0, 0, withscores=True)
                retry = 1
                if oldest:
                    retry = max(1, int(60 - (now - float(oldest[0][1]))) + 1)
                return False, retry
            return True, 0
        finally:
            await client.aclose()
