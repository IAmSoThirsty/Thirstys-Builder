"""LLM client backed by a local Ollama server.

The ThirstyAI Builder talks to a local Ollama instance (default
`http://127.0.0.1:11434`). Ollama is the only supported LLM provider; no
external keys, no stub responses, no network calls outside the local
machine.

The model is taken from the `OLLAMA_MODEL` env var (default
`qwen2.5-coder:7b`). The Ollama host is taken from `OLLAMA_HOST`
(default `http://127.0.0.1:11434`).

Dispatch:

- `configured_provider()` -> `"ollama"` if Ollama is reachable and has at
  least one model, else `"unavailable"`.
- `chat(messages, model=None)` -> dispatches to Ollama's `/api/chat`
  endpoint. Returns a dict with `model`, `content`, `provider`, and
  `done` (Ollama's stop reason). Raises `LLMUnavailable` if Ollama
  is unreachable, or `LLMError` on a non-2xx response.
- `list_models()` -> list of model names available on the local Ollama.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

DEFAULT_OLLAMA_HOST = "http://127.0.0.1:11434"
DEFAULT_OLLAMA_MODEL = "qwen2.5-coder:7b"

PROVIDER = "ollama"


class LLMUnavailable(RuntimeError):
    """The local Ollama server is unreachable or has no models."""


class LLMError(RuntimeError):
    """Ollama returned a non-2xx response."""


def _host() -> str:
    return os.environ.get("OLLAMA_HOST", DEFAULT_OLLAMA_HOST).rstrip("/")


def _model() -> str:
    return os.environ.get("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)


def list_models() -> list[str]:
    """Return the model names available on the local Ollama server.

    Returns an empty list if Ollama is unreachable. Does not raise.
    """
    try:
        with urllib.request.urlopen(f"{_host()}/api/tags", timeout=2) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return [m.get("name", "") for m in data.get("models", []) if m.get("name")]
    except (urllib.error.URLError, OSError, ValueError):
        return []


def _ollama_chat(messages: list[dict[str, str]], model: str, *, timeout: float) -> dict[str, Any]:
    """POST a chat completion to Ollama. Module-level function so tests can mock it.

    Raises `LLMUnavailable` on transport failure; `LLMError` on bad
    responses. Returns the parsed dict on success.
    """
    payload = json.dumps(
        {"model": model, "messages": messages, "stream": False}
    ).encode("utf-8")
    req = urllib.request.Request(
        f"{_host()}/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
    except (urllib.error.URLError, OSError) as exc:
        raise LLMUnavailable(f"Ollama POST {_host()}/api/chat failed: {exc}") from exc

    try:
        body = json.loads(raw)
    except ValueError as exc:
        raise LLMError(f"Ollama returned non-JSON: {raw[:200]}") from exc

    msg = body.get("message") or {}
    content = msg.get("content", "")
    if not content:
        raise LLMError(f"Ollama returned empty content. Full response: {body}")
    return {
        "model": body.get("model", model),
        "content": content,
        "provider": PROVIDER,
        "done": body.get("done", True),
        "done_reason": body.get("done_reason"),
    }


def configured_provider() -> str:
    """Return `"ollama"` if Ollama is reachable, else `"unavailable"`."""
    return "ollama" if list_models() else "unavailable"


def _normalize_model(model: str, available: list[str]) -> str:
    """If `model` is in `available` (exact or base-name), return it; else the first available."""
    if not available:
        return model
    if model in available:
        return model
    base = model.split(":")[0]
    for m in available:
        if m == model or m.split(":")[0] == base:
            return m
    return available[0]


def chat(
    messages: list[dict[str, str]],
    *,
    model: str | None = None,
    timeout: float = 120.0,
) -> dict[str, Any]:
    """Send a chat completion to the local Ollama server.

    Returns a dict with `model`, `content`, `provider`, `done`, and
    Ollama's `done_reason`. Raises `LLMUnavailable` if Ollama is
    unreachable; raises `LLMError` on non-2xx responses.
    """
    available = list_models()
    if not available:
        raise LLMUnavailable(
            f"Ollama is not reachable at {_host()}. Start it with `ollama serve` and pull a model with `ollama pull {_model()}`."
        )

    chosen = _normalize_model(model or _model(), available)
    return _ollama_chat(messages, chosen, timeout=timeout)
