"""Session log writer.

A session is one CLI invocation (one-shot or REPL). Every turn is
appended to the sessions directory passed by the caller. The
`thirsty skill distill` command reads the last N sessions and
extracts repeated tool sequences into draft skills.

The sessions directory is an explicit parameter, not a module-level
global, so tests and the CLI cannot clobber each other.
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .config import SESSIONS_DIR


@dataclass
class Turn:
    user: str
    assistant: str
    tool_calls: list[dict] = field(default_factory=list)
    skill_used: str | None = None
    ts: float = field(default_factory=time.time)


@dataclass
class Session:
    session_id: str
    started_at: float
    profile: str
    model: str
    turns: list[Turn] = field(default_factory=list)

    def add_turn(self, turn: Turn) -> None:
        self.turns.append(turn)

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)


def new_session(profile: str, model: str) -> Session:
    return Session(
        session_id=str(uuid.uuid4()),
        started_at=time.time(),
        profile=profile,
        model=model,
    )


def save(sess: Session, sessions_dir: Path = SESSIONS_DIR) -> Path:
    sessions_dir.mkdir(parents=True, exist_ok=True)
    name = time.strftime("%Y%m%dT%H%M%S", time.gmtime(sess.started_at))
    path = sessions_dir / f"{name}-{sess.session_id[:8]}.json"
    path.write_text(sess.to_json(), encoding="utf-8")
    return path


def load_recent(n: int, sessions_dir: Path = SESSIONS_DIR) -> list[Session]:
    if not sessions_dir.exists():
        return []
    files = sorted(sessions_dir.glob("*.json"), key=lambda p: p.stat().st_mtime)
    out: list[Session] = []
    for f in files[-n:]:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            turns = [Turn(**t) for t in data.get("turns", [])]
            sess = Session(
                session_id=data["session_id"],
                started_at=data["started_at"],
                profile=data.get("profile", "balanced"),
                model=data.get("model", "qwen2.5-coder:7b"),
                turns=turns,
            )
            out.append(sess)
        except (json.JSONDecodeError, KeyError, TypeError):
            continue
    return out


def tool_sequence(sess: Session) -> list[tuple[str, ...]]:
    """Return the ordered list of (tool_name, args_kind) tuples per session.

    args_kind is a coarse category so 'fix auth bug' and 'fix login
    bug' look similar. Used by distill to find repeated patterns.
    """
    seqs: list[tuple[str, ...]] = []
    for t in sess.turns:
        seq: list[str] = []
        for tc in t.tool_calls:
            name = tc.get("tool", "?")
            args = tc.get("args", {})
            kind = "any"
            if "path" in args:
                kind = "path"
            elif "pattern" in args:
                kind = "pattern"
            seq.append(f"{name}:{kind}")
        if seq:
            seqs.append(tuple(seq))
    return seqs
