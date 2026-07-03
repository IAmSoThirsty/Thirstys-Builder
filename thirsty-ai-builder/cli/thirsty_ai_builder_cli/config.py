"""Configuration loader for the ThirstyAI Builder CLI.

Reads from THIRSTY_AI_BACKEND_URL (env) and ~/.thirsty-ai-builder/config.toml
(file). First run creates the directory tree:

    ~/.thirsty-ai-builder/
    ├── config.toml        # backend URL, profile, default model
    ├── skills/             # user-installed skills (SKILL.md files)
    │   ├── code-review/
    │   ├── refactor-planner/
    │   └── _drafts/        # drafts from `thirsty skill distill`
    └── sessions/           # one JSON per session, for distill
"""
from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

CONFIG_DIR = Path.home() / ".thirsty-ai-builder"
CONFIG_PATH = CONFIG_DIR / "config.toml"
SKILLS_DIR = CONFIG_DIR / "skills"
DRAFTS_DIR = SKILLS_DIR / "_drafts"
SESSIONS_DIR = CONFIG_DIR / "sessions"

DEFAULT_BACKEND_URL = "http://127.0.0.1:8001"
DEFAULT_MODEL = "qwen2.5-coder:7b"
DEFAULT_PROFILE = "balanced"

# Named model profiles. Each maps to Ollama generation options.
# "skill level" in the user-facing sense.
PROFILES: dict[str, dict] = {
    "precise": {
        "temperature": 0.2,
        "num_ctx": 4096,
        "top_p": 0.9,
        "description": "Low-temperature, short context. For factual Q&A, audits, code review.",
    },
    "balanced": {
        "temperature": 0.7,
        "num_ctx": 8192,
        "top_p": 0.95,
        "description": "Default. General-purpose coding, refactoring, debugging.",
    },
    "creative": {
        "temperature": 0.9,
        "num_ctx": 16384,
        "top_p": 0.98,
        "description": "High-temperature, long context. For design exploration, brainstorming, naming.",
    },
}


@dataclass
class Config:
    backend_url: str = DEFAULT_BACKEND_URL
    model: str = DEFAULT_MODEL
    profile: str = DEFAULT_PROFILE
    api_key: str = ""

    @property
    def profile_options(self) -> dict:
        return PROFILES.get(self.profile, PROFILES[DEFAULT_PROFILE])

    def to_toml(self) -> str:
        return (
            f'backend_url = "{self.backend_url}"\n'
            f'model = "{self.model}"\n'
            f'profile = "{self.profile}"\n'
            f'# api_key is read from THIRSTY_AI_API_KEY env, not stored here\n'
        )


def ensure_dirs() -> None:
    """Create ~/.thirsty-ai-builder/ and subdirs on first run."""
    for d in (CONFIG_DIR, SKILLS_DIR, DRAFTS_DIR, SESSIONS_DIR):
        d.mkdir(parents=True, exist_ok=True)


def load() -> Config:
    ensure_dirs()
    cfg = Config(
        backend_url=os.environ.get("THIRSTY_AI_BACKEND_URL", DEFAULT_BACKEND_URL),
        model=os.environ.get("THIRSTY_AI_MODEL", DEFAULT_MODEL),
        profile=os.environ.get("THIRSTY_AI_PROFILE", DEFAULT_PROFILE),
        api_key=os.environ.get("THIRSTY_AI_API_KEY", ""),
    )
    if CONFIG_PATH.exists():
        data = tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        if "backend_url" in data:
            cfg.backend_url = data["backend_url"]
        if "model" in data:
            cfg.model = data["model"]
        if "profile" in data and data["profile"] in PROFILES:
            cfg.profile = data["profile"]
    return cfg


def save(cfg: Config) -> None:
    ensure_dirs()
    CONFIG_PATH.write_text(cfg.to_toml(), encoding="utf-8")
