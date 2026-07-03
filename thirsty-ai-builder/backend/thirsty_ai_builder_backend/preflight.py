"""Production preflight checks for ThirstyAI Builder deployments."""
from __future__ import annotations

import os
import re
import sys
from collections.abc import Mapping


TRUE_VALUES = {"1", "true", "yes", "on"}
PLACEHOLDER_RE = re.compile(r"(change|example|placeholder|local-verify|test-token|dummy)", re.I)


def _is_true(value: str | None) -> bool:
    return (value or "").strip().lower() in TRUE_VALUES


def validate_environment(env: Mapping[str, str]) -> list[str]:
    """Return production deployment configuration errors."""
    errors: list[str] = []

    token = env.get("CB_API_KEY", "").strip()
    if not token:
        errors.append("CB_API_KEY is required")
    elif len(token) < 32:
        errors.append("CB_API_KEY must be at least 32 characters")
    elif PLACEHOLDER_RE.search(token):
        errors.append("CB_API_KEY appears to be a placeholder/test value")

    if not _is_true(env.get("THIRSTY_AI_REQUIRE_AUTH")):
        errors.append("THIRSTY_AI_REQUIRE_AUTH must be true/1/on/yes")

    mongo_url = env.get("MONGO_URL", "").strip()
    if not mongo_url:
        errors.append("MONGO_URL is required")
    elif not (mongo_url.startswith("mongodb://") or mongo_url.startswith("mongodb+srv://")):
        errors.append("MONGO_URL must start with mongodb:// or mongodb+srv://")

    if not _is_true(env.get("THIRSTY_AI_REQUIRE_MONGO")):
        errors.append("THIRSTY_AI_REQUIRE_MONGO must be true/1/on/yes")

    origins = [item.strip() for item in env.get("CORS_ORIGINS", "").split(",") if item.strip()]
    if not origins:
        errors.append("CORS_ORIGINS must contain at least one explicit origin")
    if "*" in origins:
        errors.append("CORS_ORIGINS must not contain * in production")

    ollama_host = env.get("OLLAMA_HOST", "").strip()
    if not ollama_host:
        errors.append("OLLAMA_HOST is required")
    elif "0.0.0.0" in ollama_host:
        errors.append("OLLAMA_HOST must not point at 0.0.0.0")

    return errors


def main() -> int:
    errors = validate_environment(os.environ)
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print("PASS: thirsty-ai-builder production preflight")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
