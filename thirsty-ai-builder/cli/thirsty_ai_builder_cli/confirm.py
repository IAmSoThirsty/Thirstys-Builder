"""Confirmation token flow for write/shell tools.

The CLI prints a 6-digit code to the user; the user must type the
code back when the tool call is dispatched. The backend verifies the
code. This is real friction, not a checkbox - it stops a buggy
agent from running `rm -rf` on the user's home directory by
mistake.

The CLI generates the code, the user sees it, the user types it
back, the CLI includes it in the tool call. Codes are valid for
60 seconds and are tied to the tool+path+args hash so they cannot
be replayed.
"""
from __future__ import annotations

import hashlib
import secrets
import time


def generate(tool: str, args: dict) -> tuple[str, float]:
    """Return (6-digit code, expires_at_epoch)."""
    nonce = secrets.token_hex(8)
    digest = hashlib.sha256(f"{tool}:{sorted(args.items())}:{nonce}".encode()).hexdigest()
    code = str(int(digest[:6], 16) % 1000000).zfill(6)
    return code, time.time() + 60.0


def fingerprint(tool: str, args: dict) -> str:
    """Stable fingerprint of (tool, args) for the user to verify."""
    items = sorted((k, str(v)) for k, v in args.items())
    return hashlib.sha256(f"{tool}:{items}".encode()).hexdigest()[:12]
