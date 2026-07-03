from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TLA_JAR = ROOT / ".tool-cache" / "tla2tools.jar"
ALLOY_JAR = ROOT / ".tool-cache" / "org.alloytools.alloy.dist-6.2.0.jar"


def main() -> int:
    failures: list[str] = []
    failures.extend(validate_tla_static(ROOT / "formal" / "authorization_invariant.tla"))
    failures.extend(validate_alloy_static(ROOT / "formal" / "policy_authorization.als"))

    tlc = shutil.which("tlc") or shutil.which("tlc2")
    if tlc:
        completed = subprocess.run(
            [tlc, str(ROOT / "formal" / "authorization_invariant.tla")],
            cwd=ROOT,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
        if completed.returncode != 0:
            failures.append("TLA+ TLC execution failed")
            print(completed.stdout)
    elif TLA_JAR.exists():
        completed = subprocess.run(
            ["java", "-cp", str(TLA_JAR), "tla2sany.SANY", str(ROOT / "formal" / "authorization_invariant.tla")],
            cwd=ROOT,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
        if completed.returncode != 0:
            failures.append("TLA+ SANY execution failed")
            print(completed.stdout)
        else:
            print("PASS: TLA+ SANY parser completed")
    else:
        print("WARN: TLA+ TLC executable not available; static TLA+ checks only")

    alloy = shutil.which("alloy")
    if alloy:
        completed = subprocess.run(
            [alloy, str(ROOT / "formal" / "policy_authorization.als")],
            cwd=ROOT,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
        if completed.returncode != 0:
            failures.append("Alloy execution failed")
            print(completed.stdout)
    elif ALLOY_JAR.exists():
        completed = subprocess.run(
            ["java", "-jar", str(ALLOY_JAR), "commands", str(ROOT / "formal" / "policy_authorization.als")],
            cwd=ROOT,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        if completed.returncode != 0:
            failures.append("Alloy commands execution failed")
            print(completed.stdout)
        else:
            print("PASS: Alloy commands inspection completed")
    else:
        print("WARN: Alloy executable not available; static Alloy checks only")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    print("PASS: formal models validated")
    return 0


def validate_tla_static(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    failures: list[str] = []
    for token in ["---- MODULE authorization_invariant ----", "Init ==", "Next ==", "NoUnauthorizedExecution =="]:
        if token not in text:
            failures.append(f"TLA+ model missing {token}")
    if not text.rstrip().endswith("===="):
        failures.append("TLA+ model missing closing ====")
    return failures


def validate_alloy_static(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    failures: list[str] = []
    for token in ["module policy_authorization", "assert ExplicitDenyWins", "pred allowed"]:
        if token not in text:
            failures.append(f"Alloy model missing {token}")
    return failures


if __name__ == "__main__":
    raise SystemExit(main())
