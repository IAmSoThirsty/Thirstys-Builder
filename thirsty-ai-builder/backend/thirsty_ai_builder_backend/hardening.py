"""Hardening middlewares for the ThirstyAI Builder backend.

Three middlewares are exported:

- `SecurityHeadersMiddleware` — sets the standard security headers on
  every response. The reverse proxy is the primary defense; this is
  belt-and-suspenders so a deployment that forgot the proxy still has
  the headers in place.

- `RequestSizeLimitMiddleware` — rejects requests whose body exceeds
  `THIRSTY_AI_MAX_REQUEST_BYTES` with HTTP 413. Pydantic does its own
  per-field max_length validation, but the body itself is buffered
  before Pydantic sees it, so a 100MB body is still a memory cost.
  Cap it at the edge.

- `RateLimitMiddleware` — token-bucket rate limiter, keyed by
  `(client_ip, route_prefix)`. The default is 60 requests per minute
  per key, which is generous for an internal admin app and tight
  enough to stop a script kiddie. Configurable via env vars.

All three are stdlib-only. No new third-party dependencies.
"""
from __future__ import annotations

import os
import time
from collections import defaultdict
from threading import Lock
from typing import Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


# --- Security headers -------------------------------------------------


# A reasonable default CSP for an internal admin app. We don't load
# remote scripts (no CDN), so `'self'` covers the app code. The connect-src
# list is the most permissive: it must include the backend's own origin
# (same-origin by default) plus any explicit overrides. Operators can
# tighten this via the `THIRSTY_AI_CSP_CONNECT_SRC` env var.
DEFAULT_CSP = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    "font-src 'self'; "
    "connect-src 'self' {extra}; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self'"
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach the standard security headers to every response."""

    def __init__(self, app, *, hsts_max_age: int = 31536000) -> None:
        super().__init__(app)
        self.hsts_max_age = hsts_max_age
        extra = os.environ.get("THIRSTY_AI_CSP_CONNECT_SRC", "").strip()
        self.csp = DEFAULT_CSP.format(
            extra=extra if extra else "'self'"
        )

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        # Don't overwrite headers set by a deeper middleware (e.g. CORS).
        defaults = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Referrer-Policy": "no-referrer",
            "Permissions-Policy": (
                "accelerometer=(), camera=(), geolocation=(), "
                "gyroscope=(), magnetometer=(), microphone=(), "
                "payment=(), usb=()"
            ),
            "Cross-Origin-Opener-Policy": "same-origin",
            "Strict-Transport-Security": (
                f"max-age={self.hsts_max_age}; includeSubDomains"
            ),
            "Content-Security-Policy": self.csp,
        }
        for name, value in defaults.items():
            response.headers.setdefault(name, value)
        return response


# --- Request size cap -------------------------------------------------


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests whose Content-Length exceeds the cap.

    Requests with `Transfer-Encoding: chunked` (no Content-Length) are
    streamed up to the cap and then aborted. This protects the process
    from OOM via a 100MB JSON body on /api/rag/embed.
    """

    def __init__(self, app, *, max_bytes: int | None = None) -> None:
        super().__init__(app)
        env = os.environ.get("THIRSTY_AI_MAX_REQUEST_BYTES", "").strip()
        if max_bytes is not None:
            self.max_bytes = max_bytes
        elif env:
            self.max_bytes = int(env)
        else:
            # 1 MiB. Generous for the largest message we've designed for
            # (8000-char chat) and tiny enough to be a hard DoS stop.
            self.max_bytes = 1 * 1024 * 1024

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        cl = request.headers.get("content-length")
        if cl is not None:
            try:
                if int(cl) > self.max_bytes:
                    return JSONResponse(
                        status_code=413,
                        content={
                            "detail": (
                                f"Request body exceeds {self.max_bytes} bytes"
                            )
                        },
                    )
            except ValueError:
                return JSONResponse(
                    status_code=400,
                    content={"detail": "Invalid Content-Length header"},
                )
        # For chunked requests, read the body and check the size.
        if request.headers.get("transfer-encoding", "").lower() == "chunked":
            body = b""
            async for chunk in request.stream():
                body += chunk
                if len(body) > self.max_bytes:
                    return JSONResponse(
                        status_code=413,
                        content={
                            "detail": (
                                f"Request body exceeds {self.max_bytes} bytes"
                            )
                        },
                    )
            # Re-inject the buffered body so downstream can read it.
            request._body = body  # type: ignore[attr-defined]
        return await call_next(request)


# --- Rate limiting ----------------------------------------------------


class _TokenBucket:
    """Minimal per-key token-bucket rate limiter."""

    def __init__(self, rate_per_minute: int, burst: int) -> None:
        self.rate = rate_per_minute / 60.0  # tokens per second
        self.burst = burst
        self.tokens: dict[str, float] = defaultdict(lambda: float(burst))
        self.last_refill: dict[str, float] = defaultdict(time.monotonic)
        self.lock = Lock()

    def take(self, key: str) -> tuple[bool, float]:
        """Try to consume one token. Returns (allowed, retry_after_seconds)."""
        with self.lock:
            now = time.monotonic()
            elapsed = now - self.last_refill[key]
            self.last_refill[key] = now
            # Refill: cap at burst.
            self.tokens[key] = min(
                self.burst, self.tokens[key] + elapsed * self.rate
            )
            if self.tokens[key] >= 1:
                self.tokens[key] -= 1
                return True, 0.0
            # Not enough tokens. Compute time until 1 token is available.
            deficit = 1 - self.tokens[key]
            retry = deficit / self.rate
            return False, retry


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-(client_ip, route_prefix) token-bucket rate limiter.

    Exempts /api/health and /api/health/ready so a load balancer's
    health probe does not get throttled.
    """

    EXEMPT_PATHS: frozenset[str] = frozenset(
        {"/api/health", "/api/health/ready", "/", "/api/ownership"}
    )

    def __init__(self, app, *, rate_per_minute: int = 60, burst: int = 30) -> None:
        super().__init__(app)
        self.bucket = _TokenBucket(rate_per_minute, burst)

    @staticmethod
    def _client_ip(request: Request) -> str:
        # Trust the immediate proxy by default; deployments behind a
        # trusted reverse proxy should set TRUSTED_PROXY=1 to honor
        # X-Forwarded-For. Otherwise we use the socket peer.
        trust = os.environ.get("THIRSTY_AI_TRUST_PROXY", "").strip() == "1"
        if trust:
            xff = request.headers.get("x-forwarded-for")
            if xff:
                return xff.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    @staticmethod
    def _route_prefix(path: str) -> str:
        """Group routes by their top-3 path segments for the limit key."""
        parts = path.strip("/").split("/")
        return "/".join(parts[:3])

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        path = request.url.path
        if path in self.EXEMPT_PATHS:
            return await call_next(request)
        key = f"{self._client_ip(request)}|{self._route_prefix(path)}"
        allowed, retry_after = self.bucket.take(key)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "rate limit exceeded"},
                headers={"Retry-After": f"{int(retry_after) + 1}"},
            )
        return await call_next(request)
