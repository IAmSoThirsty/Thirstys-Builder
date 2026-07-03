from __future__ import annotations

import unittest
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class AuditChainVerification(unittest.TestCase):
    """End-to-end audit chain verification across in-memory, file-backed,
    tampered, and federation surfaces."""

    def test_audit_chain_script_passes(self) -> None:
        completed = subprocess.run(
            [sys.executable, "scripts/verify_audit_chain.py"],
            cwd=ROOT,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
        self.assertEqual(
            completed.returncode,
            0,
            f"audit chain script failed (exit {completed.returncode}):\n{completed.stdout}",
        )
        for line in completed.stdout.splitlines():
            self.assertIn("PASS:", line, f"unexpected line: {line}")


if __name__ == "__main__":
    raise SystemExit(unittest.main())
