from collections import defaultdict, deque
import logging
import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import settings


logger = logging.getLogger("dalildz.http")


class SecurityAndCorrelationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        request.state.correlation_id = correlation_id
        started = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        logger.info(
            "request.completed",
            extra={
                "correlation_id": correlation_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        response.headers["X-Request-ID"] = correlation_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; frame-ancestors 'none'; base-uri 'self'"
        )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    _hits: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        if request.url.path.endswith("/health"):
            return await call_next(request)

        key = request.client.host if request.client else "unknown"
        now = time.monotonic()
        window = self._hits[key]
        while window and now - window[0] > 60:
            window.popleft()

        if len(window) >= settings.rate_limit_per_minute:
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "RATE_LIMITED",
                        "message": "Too many requests. Retry later.",
                    }
                },
            )
        window.append(now)
        return await call_next(request)
