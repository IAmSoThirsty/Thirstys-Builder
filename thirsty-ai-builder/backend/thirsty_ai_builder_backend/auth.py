"""Authentication for the ThirstyAi Builder backend.

Single source of truth for the Bearer-token check. The token is supplied
via the `CB_API_KEY` env var. If unset, the server starts but rejects
all authenticated routes with 401. Public routes (`/`, `/api/health`,
`/api/ownership`, `/api/docs`, `/openapi.json`) are still reachable
so the system status, ownership block, and OpenAPI doc are visible
without a key.

Token format: a non-empty string. In production, generate one with
`python -c "import secrets; print(secrets.token_urlsafe(32))"` and
keep it out of the repo. The Rust CI auditor reads the same env var.

The auth dependency is reused by the FastAPI route guards and by
the background Commander audit runner.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from typing import Annotated

from fastapi import Header, HTTPException, status


# Public routes that do NOT require a token. Everything else does.
PUBLIC_PATHS: frozenset[str] = frozenset(
    {
        "/",
        "/api/health",
        "/api/ownership",
        "/docs",
        "/redoc",
        "/openapi.json",
    }
)


def _configured_token() -> str | None:
    """Return the configured token, or None if no token is set."""
    tok = os.environ.get("CB_API_KEY", "").strip()
    return tok or None


def configured() -> bool:
    """Whether a token is configured on this server."""
    return _configured_token() is not None


def _digest(token: str) -> bytes:
    return hashlib.sha256(token.encode("utf-8")).hexdigest().encode("utf-8")


def _expected_digest() -> bytes | None:
    tok = _configured_token()
    return _digest(tok) if tok is not None else None


def verify_bearer(authorization: Annotated[str | None, Header()] = None) -> str:
    """FastAPI dependency: validate the Authorization header.

    Returns the configured token (so handlers can identify the caller
    if they want). Raises 401 with `WWW-Authenticate: Bearer` on
    missing/invalid tokens. Raises 503 if no token is configured.
    """
    expected = _expected_digest()
    if expected is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="CB_API_KEY is not configured on the server. Set it in .env to enable authenticated routes.",
        )
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header. Pass `Authorization: Bearer <CB_API_KEY>`.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header must be `Bearer <token>`.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if hmac.compare_digest(_digest(parts[1]), expected):
        return parts[1]
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid token.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def constant_time_equals(a: str, b: str) -> bool:
    """Exposed for tests; not used by verify_bearer directly."""
    return hmac.compare_digest(_digest(a), _digest(b))


def generate_token() -> str:
    """Generate a fresh token. Used by the bootstrap CLI and by tests."""
    return secrets.token_urlsafe(32)
