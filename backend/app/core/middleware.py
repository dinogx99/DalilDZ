import logging
import time
import uuid
from collections import defaultdict, deque

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import settings

logger = logging.getLogger("dalildz.http")

DEFAULT_CSP = "default-src 'self'; frame-ancestors 'none'; base-uri 'self'"
DOCS_PATHS = {"/docs", "/docs/oauth2-redirect", "/redoc"}
DOCS_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
    "font-src 'self' https://fonts.gstatic.com; "
    "img-src 'self' data: https://fastapi.tiangolo.com; "
    "worker-src 'self' blob:; frame-ancestors 'none'; base-uri 'self'"
)


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
        if "content-security-policy" not in response.headers:
            path = request.url.path
            if path in DOCS_PATHS:
                # Swagger UI / ReDoc load their bundles from jsDelivr and use inline bootstrap code.
                response.headers["Content-Security-Policy"] = DOCS_CSP
            else:
                response.headers["Content-Security-Policy"] = DEFAULT_CSP
        return response


MAX_TRACKED_CLIENTS = 10_000


class RateLimitMiddleware(BaseHTTPMiddleware):
    _hits: dict[str, deque[float]] = defaultdict(deque)

    def _evict_stale(self, now: float) -> None:
        # Keep the in-memory table bounded: drop clients without hits in the last minute.
        stale = [key for key, hits in self._hits.items() if not hits or now - hits[-1] > 60]
        for key in stale:
            del self._hits[key]

    async def dispatch(self, request: Request, call_next):
        if request.url.path.endswith("/health"):
            return await call_next(request)

        key = request.client.host if request.client else "unknown"
        now = time.monotonic()
        if len(self._hits) > MAX_TRACKED_CLIENTS:
            self._evict_stale(now)
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
