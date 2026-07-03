"""ThirstyAI Builder CLI - main entry point.

Subcommands:
    thirsty                              # REPL
    thirsty "fix the auth bug"           # one-shot
    thirsty --profile precise "..."      # named model profile
    thirsty config show                  # print effective config
    thirsty config set <key> <value>     # update config.toml
    thirsty skill list                   # loaded skills
    thirsty skill list --drafts          # draft skills (unapproved)
    thirsty skill show <name>            # print a skill
    thirsty skill new <name>             # scaffold a new skill directory
    thirsty skill edit <name>            # open SKILL.md in $EDITOR
    thirsty skill distill --last 10      # extract patterns from sessions
    thirsty skill approve <name>         # promote a draft to live
    thirsty skill reject <name>          # delete a draft
    thirsty session list                 # recent session logs
    thirsty doctor                       # connectivity + config check
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from . import __version__
from . import client, session
from . import skills as skills_mod
from . import confirm
from .config import (
    CONFIG_PATH, DRAFTS_DIR, SKILLS_DIR, SESSIONS_DIR, Config,
    PROFILES, ensure_dirs, load, save,
)


def _print_banner(cfg: Config) -> None:
    print(f"thirsty {__version__}  model={cfg.model}  profile={cfg.profile}  backend={cfg.backend_url}")


def _repl(cfg: Config) -> int:
    _print_banner(cfg)
    print("Type a message, or ':q' to quit. ':help' for commands.")
    sess = session.new_session(cfg.profile, cfg.model)
    skills = skills_mod.load_all(SKILLS_DIR)
    print(f"loaded {len(skills)} skill(s): {', '.join(s.name for s in skills) or '(none)'}")
    while True:
        try:
            line = input("\nthirsty> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        if line in (":q", ":quit", ":exit"):
            break
        if line == ":help":
            _repl_help()
            continue
        if line.startswith(":skills"):
            print(", ".join(s.name for s in skills) or "(none)")
            continue
        if line.startswith(":profile "):
            new = line.split(" ", 1)[1].strip()
            if new in PROFILES:
                cfg.profile = new
                print(f"profile -> {new}")
            else:
                print(f"unknown profile. choices: {', '.join(PROFILES)}")
            continue
        turn = _one_turn(cfg, line, skills)
        sess.add_turn(turn)
    session.save(sess)
    print(f"session saved: {sess.session_id[:8]}")
    return 0


def _repl_help() -> None:
    print("""\
:q / :quit / :exit   leave
:help                this help
:skills              list loaded skills
:profile <name>      switch profile (precise|balanced|creative)""")


def _one_turn(cfg: Config, message: str, skills: list[skills_mod.Skill]) -> session.Turn:
    matched = skills_mod.match_skill(skills, message)
    if matched is not None:
        print(f"[skill] {matched.name}  ({matched.description})")
    try:
        resp = client.chat(cfg, message, profile=cfg.profile)
        answer = resp.get("answer") or resp.get("response") or json.dumps(resp)
    except client.ThirstyAIError as e:
        answer = f"[backend error] {e}"
    print(answer)
    return session.Turn(
        user=message,
        assistant=str(answer),
        skill_used=matched.name if matched else None,
    )


def _one_shot(cfg: Config, message: str) -> int:
    _print_banner(cfg)
    skills = skills_mod.load_all(SKILLS_DIR)
    sess = session.new_session(cfg.profile, cfg.model)
    sess.add_turn(_one_turn(cfg, message, skills))
    session.save(sess)
    return 0


def _config_show(cfg: Config) -> int:
    print(f"config file:  {CONFIG_PATH}")
    print(f"backend_url:  {cfg.backend_url}")
    print(f"model:        {cfg.model}")
    print(f"profile:      {cfg.profile}")
    print(f"  -> {PROFILES[cfg.profile]['description']}")
    print(f"api_key:      {'set' if cfg.api_key else '(unset; set THIRSTY_AI_API_KEY)'}")
    return 0


def _config_set(cfg: Config, key: str, value: str) -> int:
    if key == "backend_url":
        cfg.backend_url = value
    elif key == "model":
        cfg.model = value
    elif key == "profile":
        if value not in PROFILES:
            print(f"unknown profile. choices: {', '.join(PROFILES)}")
            return 1
        cfg.profile = value
    else:
        print(f"unknown config key: {key}")
        return 1
    save(cfg)
    print(f"{key} = {value}  (saved to {CONFIG_PATH})")
    return 0


def _skill_list(args: argparse.Namespace) -> int:
    if args.drafts:
        for s in skills_mod.load_drafts(DRAFTS_DIR):
            marker = "[DRAFT]" if s.is_draft else ""
            print(f"{marker} {s.name:30s} {s.description}")
        return 0
    for s in skills_mod.load_all(SKILLS_DIR):
        print(f"{s.name:30s} {s.description}")
    drafts = skills_mod.load_drafts(DRAFTS_DIR)
    if drafts:
        print(f"\n{len(drafts)} draft(s) - run 'thirsty skill approve <name>' to promote")
    return 0


def _skill_show(name: str) -> int:
    skill_dir = SKILLS_DIR / name
    if not (skill_dir / "SKILL.md").exists():
        print(f"no such skill: {name}")
        return 1
    print((skill_dir / "SKILL.md").read_text(encoding="utf-8"))
    return 0


def _skill_new(name: str) -> int:
    safe = "".join(c for c in name if c.isalnum() or c in "-_").lower()
    if not safe:
        print("invalid skill name")
        return 1
    skill_dir = SKILLS_DIR / safe
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        skill_md.write_text(skills_mod.render_skill(skills_mod.Skill(
            name=safe,
            description="TODO: describe what this skill does and when to use it.",
            tools=[],
            body="# Steps\n\n1. TODO\n",
            path=skill_md,
        )), encoding="utf-8")
    print(f"created {skill_md}")
    print("next: edit the file, then it loads on next `thirsty` launch.")
    return 0


def _skill_edit(name: str) -> int:
    skill_md = SKILLS_DIR / name / "SKILL.md"
    if not skill_md.exists():
        print(f"no such skill: {name}")
        return 1
    editor = os.environ.get("EDITOR", "notepad" if os.name == "nt" else "vi")
    return subprocess.call([editor, str(skill_md)])


def _skill_distill(args: argparse.Namespace) -> int:
    """Self-improvement loop.

    Reads the last N session logs, asks Ollama (via the backend) to
    extract repeated tool sequences, and writes a draft SKILL.md for
    each pattern that appears >= --min-occurrences times. Drafts go
    to ~/.thirsty-ai-builder/skills/_drafts/<name>/ and require
    `thirsty skill approve <name>` to be promoted.
    """
    n = args.last
    min_occ = args.min_occurrences
    sessions = session.load_recent(n)
    if not sessions:
        print("no sessions to distill")
        return 0
    sequences: dict[tuple[str, ...], int] = {}
    for s in sessions:
        for seq in session.tool_sequence(s):
            sequences[seq] = sequences.get(seq, 0) + 1
    if not sequences:
        print("no tool sequences found in recent sessions")
        return 0
    repeated = {seq: count for seq, count in sequences.items() if count >= min_occ}
    if not repeated:
        print(f"no sequence appeared {min_occ}+ times. (found {len(sequences)} unique)")
        return 0
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    for i, (seq, count) in enumerate(sorted(repeated.items(), key=lambda x: -x[1]), start=1):
        name = f"distill-{i:02d}-{seq[0].split(':')[0]}"
        body_md = (
            f"# Auto-distilled skill\n\n"
            f"Pattern observed {count} times across the last {n} sessions:\n\n"
            f"```\n" + "\n".join(f"  {step}" for step in seq) + "\n```\n\n"
            f"## Steps\n\n"
            f"1. TODO: refine the steps based on the observed pattern.\n"
        )
        skill = skills_mod.Skill(
            name=name,
            description=f"Auto-distilled from {count} sessions: {' -> '.join(seq)}",
            tools=[s.split(":")[0] for s in seq],
            body=body_md,
            path=DRAFTS_DIR / name / "SKILL.md",
            is_draft=True,
        )
        skill.path.parent.mkdir(parents=True, exist_ok=True)
        skill.path.write_text(skills_mod.render_skill(skill), encoding="utf-8")
        print(f"draft: {name}  ({count} occurrences)")
    print(f"\n{len(repeated)} draft(s) written. Review with 'thirsty skill list --drafts'.")
    print("Promote with 'thirsty skill approve <name>' or discard with 'thirsty skill reject <name>'.")
    return 0


def _skill_approve(name: str) -> int:
    src = DRAFTS_DIR / name / "SKILL.md"
    if not src.exists():
        print(f"no such draft: {name}")
        return 1
    dst = SKILLS_DIR / name / "SKILL.md"
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    import shutil
    shutil.rmtree(DRAFTS_DIR / name)
    print(f"approved: {name}  ->  {dst}")
    return 0


def _skill_reject(name: str) -> int:
    import shutil
    target = DRAFTS_DIR / name
    if not target.exists():
        print(f"no such draft: {name}")
        return 1
    shutil.rmtree(target)
    print(f"rejected: {name}")
    return 0


def _session_list() -> int:
    if not SESSIONS_DIR.exists():
        print("(no sessions)")
        return 0
    files = sorted(SESSIONS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    for f in files[:20]:
        size = f.stat().st_size
        print(f"{f.name:60s} {size:>6d} bytes")
    return 0


def _doctor(cfg: Config) -> int:
    print(f"thirsty {__version__}")
    print(f"backend: {cfg.backend_url}")
    print(f"model:   {cfg.model}")
    print(f"profile: {cfg.profile}")
    print(f"api_key: {'set' if cfg.api_key else 'UNSET - set THIRSTY_AI_API_KEY'}")
    print()
    try:
        h = client.health(cfg)
        print(f"backend health: {h.get('status')}  product={h.get('product')}")
        print(f"  llm_provider:  {h.get('llm_provider')}")
        print(f"  ollama:        {h.get('ollama')}")
    except client.ThirstyAIError as e:
        print(f"backend unreachable: {e}")
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="thirsty",
        description="ThirstyAI Builder CLI - local coding agent backed by your ThirstyAI Builder.",
    )
    p.add_argument("--profile", choices=list(PROFILES), help="model profile (skill level)")
    p.add_argument("--backend", help="backend URL (overrides config + env)")
    p.add_argument("--model", help="Ollama model name (overrides config + env)")
    p.add_argument("--api-key", help="bearer token (overrides env)")
    p.add_argument("--version", action="version", version=f"thirsty {__version__}")
    p.add_argument("message", nargs="*", help="message (one-shot mode)")

    sub = p.add_subparsers(dest="cmd")

    sub.add_parser("config").add_parser("show")
    cfg_set = sub.add_parser("config").add_parser("set")
    cfg_set.add_argument("key")
    cfg_set.add_argument("value")

    skill = sub.add_parser("skill")
    skill_sub = skill.add_subparsers(dest="skill_cmd")
    sl = skill_sub.add_parser("list")
    sl.add_argument("--drafts", action="store_true")
    ss = skill_sub.add_parser("show")
    ss.add_argument("name")
    sn = skill_sub.add_parser("new")
    sn.add_argument("name")
    se = skill_sub.add_parser("edit")
    se.add_argument("name")
    sd = skill_sub.add_parser("distill")
    sd.add_argument("--last", type=int, default=10, help="how many recent sessions to read")
    sd.add_argument("--min-occurrences", type=int, default=3, help="min repeat count to qualify")
    sa = skill_sub.add_parser("approve")
    sa.add_argument("name")
    sr = skill_sub.add_parser("reject")
    sr.add_argument("name")

    sub.add_parser("session").add_parser("list")
    sub.add_parser("doctor")

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    ensure_dirs()
    cfg = load()
    if args.backend:
        cfg.backend_url = args.backend
    if args.model:
        cfg.model = args.model
    if args.api_key:
        cfg.api_key = args.api_key
    if args.profile:
        cfg.profile = args.profile

    if args.cmd == "config":
        if len(args.message) >= 1 and args.message[0] == "show":
            return _config_show(cfg)
        if len(args.message) >= 3 and args.message[0] == "set":
            return _config_set(cfg, args.message[1], args.message[2])
        return _config_show(cfg)
    if args.cmd == "skill":
        if args.skill_cmd == "list":
            return _skill_list(args)
        if args.skill_cmd == "show":
            return _skill_show(args.name)
        if args.skill_cmd == "new":
            return _skill_new(args.name)
        if args.skill_cmd == "edit":
            return _skill_edit(args.name)
        if args.skill_cmd == "distill":
            return _skill_distill(args)
        if args.skill_cmd == "approve":
            return _skill_approve(args.name)
        if args.skill_cmd == "reject":
            return _skill_reject(args.name)
    if args.cmd == "session":
        return _session_list()
    if args.cmd == "doctor":
        return _doctor(cfg)

    if args.message:
        return _one_shot(cfg, " ".join(args.message))
    return _repl(cfg)


if __name__ == "__main__":
    sys.exit(main())
