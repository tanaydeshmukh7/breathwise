"""Sliding-window rate limiter dependency for FastAPI routes."""

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

from app.config import get_settings


class SlidingWindowRateLimiter:
    """In-memory sliding-window rate limiter keyed by client IP + route group."""

    def __init__(self, group: str, max_requests_getter) -> None:
        self.group = group
        self.max_requests_getter = max_requests_getter
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    async def __call__(self, request: Request) -> None:
        client_host = request.client.host if request.client else "unknown"
        forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        ip = forwarded or client_host
        key = f"{self.group}:{ip}"
        now = time.monotonic()
        window_start = now - 60.0
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
