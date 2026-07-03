from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TLA_JAR = ROOT / ".tool-cache" / "tla2tools.jar"
ALLOY_JAR = ROOT / ".tool-cache" / "org.alloytools.alloy.dist-6.2.0.jar"
TLA_FILE = ROOT / "formal" / "authorization_invariant.tla"
TLA_CFG = ROOT / "formal" / "authorization_invariant.cfg"


def main() -> int:
    failures: list[str] = []
    failures.extend(validate_tla_static(TLA_FILE))
    failures.extend(validate_alloy_static(ROOT / "formal" / "policy_authorization.als"))

    failures.extend(run_tlc())

    failures.extend(run_alloy())

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    print("PASS: formal models validated")
    return 0


def run_tlc() -> list[str]:
    """Run SANY parser + TLC bounded model check on the TLA+ model.

    Order matters: SANY parses and reports syntax/semantic errors; if SANY
    passes, TLC does the bounded state-space exploration. Both must pass
    for the formal gate to be green.
    """
    failures: list[str] = []
    tlc = shutil.which("tlc") or shutil.which("tlc2")
    use_jar = tlc is None and TLA_JAR.exists()
    if tlc is None and not use_jar:
        print("WARN: TLA+ TLC executable not available; static TLA+ checks only")
        return failures

    if use_jar:
        sany_cmd = [
            "java",
            "-cp",
            str(TLA_JAR),
            "tla2sany.SANY",
            str(TLA_FILE),
        ]
        tlc_cmd = [
            "java",
            "-XX:+UseParallelGC",
            "-cp",
            str(TLA_JAR),
            "tlc2.TLC",
            "-nowarning",
            str(TLA_FILE.relative_to(ROOT)),
            "-config",
            str(TLA_CFG.relative_to(ROOT)),
            "-workers",
            "1",
        ]
        cwd = ROOT
    else:
        # tlc CLI present: use it directly with cwd=formal so SANY sees the
        # module name == file basename.
        sany_cmd = [tlc, str(TLA_FILE)]
        tlc_cmd = [
            tlc,
            "-nowarning",
            TLA_FILE.name,
            "-config",
            TLA_CFG.name,
            "-workers",
            "1",
        ]
        cwd = TLA_FILE.parent

    completed = subprocess.run(
        sany_cmd, cwd=cwd, check=False, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
        timeout=60,
    )
    if completed.returncode != 0:
        failures.append("TLA+ SANY execution failed")
        print(completed.stdout)
        return failures
    print("PASS: TLA+ SANY parser completed")

    completed = subprocess.run(
        tlc_cmd, cwd=cwd, check=False, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
        timeout=180,
    )
    if completed.returncode != 0:
        failures.append("TLA+ TLC bounded model check failed")
        print(completed.stdout)
        return failures
    tail = completed.stdout.strip().splitlines()[-3:]
    summary = " | ".join(line.strip() for line in tail if line.strip())
    print(f"PASS: TLA+ TLC bounded model check completed ({summary})")
    return failures


def run_alloy() -> list[str]:
    """Run Alloy commands inspection on the policy authorization model."""
    failures: list[str] = []
    alloy = shutil.which("alloy")
    use_jar = alloy is None and ALLOY_JAR.exists()
    if alloy is None and not use_jar:
        print("WARN: Alloy executable not available; static Alloy checks only")
        return failures

    if use_jar:
        cmd = [
            "java", "-jar", str(ALLOY_JAR), "commands",
            str(ROOT / "formal" / "policy_authorization.als"),
        ]
    else:
        cmd = [alloy, str(ROOT / "formal" / "policy_authorization.als")]

    completed = subprocess.run(
        cmd, cwd=ROOT, check=False, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
        timeout=30,
    )
    if completed.returncode != 0:
        failures.append("Alloy commands execution failed")
        print(completed.stdout)
        return failures
    print("PASS: Alloy commands inspection completed")
    return failures


def validate_tla_static(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    failures: list[str] = []
    for token in [
        "---- MODULE authorization_invariant ----",
        "Init ==",
        "Next ==",
        "NoUnauthorizedExecution ==",
        "TypeOK ==",
    ]:
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
