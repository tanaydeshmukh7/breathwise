"""Sliding-window rate limiter dependency for FastAPI routes."""

import time
from collections import defaultdict, deque
from typing import Callable

from fastapi import HTTPException, Request, status

from app.config import get_settings


class SlidingWindowRateLimiter:
    """In-memory sliding-window rate limiter keyed by client IP + route group."""

    _MAX_TRACKED_KEYS = 2000

    def __init__(self, group: str, max_requests_getter: Callable[[], int]) -> None:
        self.group = group
        self.max_requests_getter = max_requests_getter
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    @staticmethod
    def _extract_client_ip(request: Request) -> str:
        # Prefer proxy-provided real IP headers, then direct socket peer.
        real_ip = (request.headers.get("x-real-ip") or "").strip()
        if real_ip:
            return real_ip
        forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        if forwarded:
            return forwarded
        return request.client.host if request.client else "unknown"

    def _prune_stale(self, window_start: float) -> None:
        if len(self._hits) <= self._MAX_TRACKED_KEYS:
            return
        stale = [k for k, q in self._hits.items() if not q or q[-1] < window_start]
        for k in stale:
            del self._hits[k]

    async def __call__(self, request: Request) -> None:
        ip = self._extract_client_ip(request)
        key = f"{self.group}:{ip}"
        now = time.monotonic()
        window_start = now - 60.0
        self._prune_stale(window_start)
        bucket = self._hits[key]
        while bucket and bucket[0] < window_start:
            bucket.popleft()
        limit = self.max_requests_getter()
        if len(bucket) >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded for {self.group} requests. Please retry in a minute.",
            )
        bucket.append(now)


ai_rate_limiter = SlidingWindowRateLimiter(
    "ai", lambda: get_settings().AI_RATE_LIMIT_PER_MINUTE
)
auth_rate_limiter = SlidingWindowRateLimiter(
    "auth", lambda: get_settings().AUTH_RATE_LIMIT_PER_MINUTE
)
