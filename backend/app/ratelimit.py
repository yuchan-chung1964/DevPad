"""In-memory sliding-window rate limiter. Per-process: use a shared store (Redis) if you run several workers."""
import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException

from app.config import RATE_LIMIT_WINDOW_SECONDS


class RateLimiter:
    def __init__(self, window: float = RATE_LIMIT_WINDOW_SECONDS):
        self.window = window
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()
        self._calls = 0

    def check(self, key: str, limit: int) -> None:
        """Record a hit for `key`; raise 429 if it already made `limit` hits within the window."""
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] >= self.window:
                hits.popleft()
            if len(hits) >= limit:
                retry = max(1, int(self.window - (now - hits[0])) + 1)
                raise HTTPException(429, "Too many requests", headers={"Retry-After": str(retry)})
            hits.append(now)
            self._calls += 1
            if self._calls % 1000 == 0:
                self._evict(now)

    def _evict(self, now: float) -> None:
        for k in [k for k, h in self._hits.items() if not h or now - h[-1] >= self.window]:
            del self._hits[k]

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


limiter = RateLimiter()


def enforce_quota(current: int, limit: int, what: str) -> None:
    if current >= limit:
        raise HTTPException(403, f"Quota exceeded: at most {limit} {what}")
