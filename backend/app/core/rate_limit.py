"""In-process sliding-window rate limiter.

Per-process state is sufficient for a single backend instance; a Redis-backed
limiter can replace this without changing the middleware contract.
"""

import time
from collections import defaultdict, deque
from typing import Dict, Tuple


class RateLimiter:
    def __init__(self, default_limit: int = 120):
        self.default_limit = default_limit
        self._events: Dict[str, deque] = defaultdict(deque)

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
