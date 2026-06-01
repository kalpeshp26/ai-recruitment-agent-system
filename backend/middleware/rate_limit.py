"""
--- FILE: backend/middleware/rate_limit.py ---

Simple in-memory rate limiter for auth routes: 10 req/min per user.
Note: In-memory limiter is suitable for single-process dev only.
"""
import time
from fastapi import Request, HTTPException, status

RATE_LIMIT = 10
WINDOW_SECONDS = 60

_user_requests = {}


async def rate_limit_middleware(request: Request):
    """Raise HTTPException 429 if requests exceed RATE_LIMIT per WINDOW_SECONDS."""
    # Apply only to auth routes
    if request.url.path.startswith("/api/v1/interview/") and request.method == "POST":
        user = request.client.host if request.client else "anon"
        now = time.time()
        window = _user_requests.get(user, [])
        # prune
        window = [t for t in window if now - t < WINDOW_SECONDS]
        if len(window) >= RATE_LIMIT:
            raise HTTPException(status_code=429, detail="rate_limit_exceeded")
        window.append(now)
        _user_requests[user] = window
