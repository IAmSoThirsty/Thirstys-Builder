"""Skill loader for the ThirstyAI Builder CLI.

Skills are declarative Markdown files with YAML frontmatter:

    ---
    name: code-review
    description: Read a source file and return a structured review.
    tools: [read]
    ---
    # Steps
    1. Read the file at <path>
    2. Return a review with sections: correctness, security, style.

The CLI loads all skills from ~/.thirsty-ai-builder/skills/ on
launch. For each user message, it picks the best-matching skill by
description similarity (keyword overlap; not embedding-based) and
injects the skill body into the system prompt.

Drafts in _drafts/ are NOT loaded - they require `thirsty skill
approve <name>` to be promoted into the live skills/ directory.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Skill:
    name: str
    description: str
    tools: list[str]
    body: str
    path: Path
    is_draft: bool = False


FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)


def parse_skill_file(path: Path, is_draft: bool = False) -> Skill | None:
    """Parse a SKILL.md file. Returns None on parse error."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None
    fm, body = m.group(1), m.group(2)
    name = path.parent.name
    description = ""
    tools: list[str] = []
    for line in fm.splitlines():
        line = line.strip()
        if line.startswith("name:"):
            name = line.split(":", 1)[1].strip()
        elif line.startswith("description:"):
            description = line.split(":", 1)[1].strip()
        elif line.startswith("tools:"):
            raw = line.split(":", 1)[1].strip()
            tools = [t.strip() for t in raw.strip("[]").split(",") if t.strip()]
    return Skill(
        name=name, description=description, tools=tools,
        body=body.strip(), path=path, is_draft=is_draft,
    )


def load_all(skills_dir: Path) -> list[Skill]:
    """Load all live (non-draft) skills from skills_dir/."""
    out: list[Skill] = []
    if not skills_dir.exists():
        return out
    for child in sorted(skills_dir.iterdir()):
        if not child.is_dir() or child.name.startswith("_") or child.name.startswith("."):
            continue
        skill_md = child / "SKILL.md"
        if not skill_md.exists():
            continue
        s = parse_skill_file(skill_md, is_draft=False)
        if s is not None:
            out.append(s)
    return out


def load_drafts(drafts_dir: Path) -> list[Skill]:
    """Load draft skills from skills_dir/_drafts/."""
    out: list[Skill] = []
    if not drafts_dir.exists():
        return out
    for child in sorted(drafts_dir.iterdir()):
        if not child.is_dir() or child.name.startswith("."):
            continue
        skill_md = child / "SKILL.md"
        if not skill_md.exists():
            continue
        s = parse_skill_file(skill_md, is_draft=True)
        if s is not None:
            out.append(s)
    return out


def _tokenize(s: str) -> set[str]:
    return {w.lower() for w in re.findall(r"[a-zA-Z0-9_-]+", s) if len(w) > 2}


def match_skill(skills: list[Skill], user_message: str) -> Skill | None:
    """Return the skill with the highest description/user-message overlap.

    Not embedding-based; simple token overlap. Returns None if no
    skill has any overlap.
    """
    msg_tokens = _tokenize(user_message)
    if not msg_tokens:
        return None
    best: tuple[int, Skill] | None = None
    for s in skills:
        score = len(msg_tokens & _tokenize(s.description))
        if score == 0:
            continue
        if best is None or score > best[0]:
            best = (score, s)
    return best[1] if best else None


def build_system_prompt(skills: list[Skill], base: str) -> str:
    """Inject the matched skill (if any) into the system prompt.

    `base` is the default ThirstyAI Builder system prompt. If a skill
    is matched, the skill body is appended under a '## Active skill'
    heading.
    """
    return base  # No auto-injection at this stage; the CLI REPL picks
                 # a skill per turn and prepends it. See session.py.


def render_skill(skill: Skill) -> str:
    """Render a Skill to its on-disk SKILL.md form."""
    tools_repr = "[" + ", ".join(skill.tools) + "]"
    return (
        f"---\n"
        f"name: {skill.name}\n"
        f"description: {skill.description}\n"
        f"tools: {tools_repr}\n"
        f"---\n"
        f"{skill.body}\n"
    )
