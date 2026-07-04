"""ThirstyAI Builder CLI.

A local coding agent that talks to the ThirstyAI Builder backend. The
CLI is the on-ramp for terminal-driven work: it reads user input,
loads skills from ~/.thirsty-ai-builder/skills/, dispatches tool calls
to the backend, and persists session history so the user can distill
repeated patterns into new skills (`thirsty skill distill`).

Activation:
    pip install -e thirsty-ai-builder/cli
    thirsty                              # REPL
    thirsty "fix the auth bug"           # one-shot
    thirsty --profile precise "..."      # named model profile
    thirsty skill list                   # loaded skills
    thirsty skill distill --last 10      # extract patterns from sessions
    thirsty skill approve <name>         # promote a draft
    thirsty skill reject <name>          # discard a draft
    thirsty skill edit <name>            # open SKILL.md in $EDITOR

See thirsty-ai-builder/docs/CLI.md for the full reference.
"""
from __future__ import annotations

__version__ = "0.3.1"
