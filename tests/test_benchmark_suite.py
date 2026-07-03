from __future__ import annotations

import unittest
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


class BenchmarkSuiteSmoke(unittest.TestCase):
    """Smoke test for the benchmark suite.

    Runs the benchmark suite with a small iteration count to keep the
    unittest gate fast. The full 1000-iteration suite is run by
    `scripts/verify_all.py`.
    """

    def test_benchmark_suite_smoke(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "benchmarks/benchmark_suite.py",
                "--iterations",
                "50",
            ],
            cwd=ROOT,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
        self.assertEqual(
            completed.returncode,
            0,
            f"benchmark suite failed (exit {completed.returncode}):\n{completed.stdout}",
        )
        for line in completed.stdout.splitlines():
            if line.startswith("PASS: benchmark "):
                self.assertIn("PASS", line)


if __name__ == "__main__":
    raise SystemExit(unittest.main())
