"""Backend HTTP client for the ThirstyAI Builder CLI.

The CLI talks to the Builder backend over HTTP. The bearer token
(THIRSTY_AI_API_KEY) is sent on every request. Every call returns a
dict on success or raises ThirstyAIError on failure.

The client is intentionally small and synchronous - the CLI is a
single-user tool, not a server.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from .config import Config


class ThirstyAIError(Exception):
    """Raised when the backend returns a non-2xx response."""


def _request(cfg: Config, method: str, path: str, body: dict | None = None) -> dict:
    url = cfg.backend_url.rstrip("/") + path
    data = None
    headers = {"Accept": "application/json"}
    if cfg.api_key:
        headers["Authorization"] = f"Bearer {cfg.api_key}"
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise ThirstyAIError(f"HTTP {e.code} from {path}: {detail}") from None
    except urllib.error.URLError as e:
        raise ThirstyAIError(f"cannot reach {cfg.backend_url}: {e.reason}") from None


def chat(cfg: Config, message: str, profile: str | None = None) -> dict:
    """Send a message to /api/dove and return the response dict."""
    return _request(cfg, "POST", "/api/dove", {
        "message": message,
        "profile": profile or cfg.profile,
    })


def tool_call(cfg: Config, tool: str, args: dict, confirm_token: str | None = None) -> dict:
    """Dispatch a tool call to /api/tools/{tool}.

    confirm_token is required for write and shell tools. The CLI prints
    the token to the user; the user types it back. The backend refuses
    write/shell calls without a valid token.
    """
    body = {"args": args}
    if confirm_token is not None:
        body["confirm_token"] = confirm_token
    return _request(cfg, "POST", f"/api/tools/{tool}", body)


def list_skills_remote(cfg: Config) -> dict:
    """List server-side skill metadata from /api/tools/appstore."""
    return _request(cfg, "GET", "/api/tools/appstore")


def health(cfg: Config) -> dict:
    """GET /api/health - no auth required."""
    return _request(cfg, "GET", "/api/health")
