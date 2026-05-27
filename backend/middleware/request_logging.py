"""
--- FILE: backend/middleware/request_logging.py ---

Structured JSON request logging middleware.
"""
import logging
import json
from fastapi import Request

logger = logging.getLogger("interview.request")


async def log_request(request: Request, call_next):
    """Log request details as JSON and pass through to next handler."""
    start = request.scope.get("start_time")
    try:
        response = await call_next(request)
        info = {
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
        }
        logger.info(json.dumps(info))
        return response
    except Exception as e:
        logger.exception("Request handling failed: %s", e)
        raise
