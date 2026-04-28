from __future__ import annotations

import time
from collections import defaultdict, deque


class WsRateLimiter:
    """Simple in-memory per-client sliding-window rate limiter."""

    def __init__(self, max_events_per_minute: int = 120) -> None:
        self.max_events = max_events_per_minute
        self._events: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, client_id: str) -> bool:
        now = time.time()
        bucket = self._events[client_id]
        cutoff = now - 60.0

        while bucket and bucket[0] < cutoff:
            bucket.popleft()

        if len(bucket) >= self.max_events:
            return False

        bucket.append(now)
        return True
