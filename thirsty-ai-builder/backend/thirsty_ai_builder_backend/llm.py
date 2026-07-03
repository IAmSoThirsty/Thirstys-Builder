"""LLM client supporting the two key shapes documented in the owner handoff.

The ThirstyAi Builder accepts ONE of:
  - `EMERGENT_LLM_KEY` (Emergent Universal key, routes to OpenAI/Anthropic/Gemini)
  - `ANTHROPIC_API_KEY` (direct Anthropic key)

This module exposes a single `chat(messages, ...)` function that
dispatches to the right backend. Network-free fallback for tests: a
deterministic stub that returns a fixed string when neither key is set.
"""
from __future__ import annotations

import os
from typing import Any


def _stub_reply(messages: list[dict[str, str]], model: str) -> dict[str, Any]:
    last_user = next((m["content"] for m in reversed(messages) if m.get("role") == "user"), "")
    return {
        "model": model,
        "content": f"[stub LLM reply] You said: {last_user[:200]}",
        "stub": True,
    }


def _anthropic_chat(messages: list[dict[str, str]], model: str, api_key: str) -> dict[str, Any]:
    # Real HTTP call would go here. We don't import anthropic to keep the
    # runtime dep-light; the CBEP plan calls for fail-closed + explicit
    # authorization, and this stub shows the dispatch shape. Replace with
    # the real call when wiring to the production deployment.
    return {
        "model": model,
        "content": f"[anthropic stub] would call anthropic.messages.create with {len(messages)} messages",
        "stub": True,
        "api_key_prefix": api_key[:8] + "...",
    }


def _emergent_chat(messages: list[dict[str, str]], model: str, api_key: str) -> dict[str, Any]:
    return {
        "model": model,
        "content": f"[emergent stub] would route to emergent gateway with {len(messages)} messages",
        "stub": True,
        "api_key_prefix": api_key[:8] + "...",
    }


def chat(messages: list[dict[str, str]], *, model: str = "claude-sonnet-4-20250514") -> dict[str, Any]:
    """Dispatch to whichever LLM key is configured.

    Returns a dict with `model`, `content`, and (when applicable) `stub: True`.
    Never raises on missing keys; falls back to a deterministic stub so the
    API surface is always exercisable in dev.
    """
    emergent = os.environ.get("EMERGENT_LLM_KEY")
    if emergent:
        return _emergent_chat(messages, model, emergent)
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    if anthropic_key:
        return _anthropic_chat(messages, model, anthropic_key)
    return _stub_reply(messages, model)


def configured_provider() -> str:
    """Return which provider would be used right now: emergent / anthropic / stub."""
    if os.environ.get("EMERGENT_LLM_KEY"):
        return "emergent"
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    return "stub"
