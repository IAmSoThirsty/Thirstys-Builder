from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


COMMANDS = [
    [sys.executable, "-m", "compileall", "-q", "source", "tests", "scripts", "benchmarks"],
    [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
    [sys.executable, "scripts/validate_repository.py"],
    [sys.executable, "scripts/validate_api_contracts.py"],
    [sys.executable, "scripts/model_check_authorization.py"],
    [sys.executable, "scripts/install_formal_tools.py"],
    [sys.executable, "scripts/validate_formal_models.py"],
    [sys.executable, "scripts/fuzz_kernel_authorization.py"],
    [sys.executable, "scripts/property_fuzz_kernel_authorization.py"],
    [sys.executable, "scripts/run_conformance.py"],
    [sys.executable, "scripts/run_grpc_conformance.py"],
    [sys.executable, "scripts/run_cluster_conformance.py"],
    [sys.executable, "scripts/run_chaos_checks.py"],
    [sys.executable, "scripts/generate_release_evidence.py", "--check"],
    [sys.executable, "scripts/build_release_package.py", "--check"],
    [sys.executable, "scripts/sign_release_package.py", "--check"],
    [sys.executable, "scripts/validate_deployment.py"],
    [sys.executable, "scripts/verify_audit_chain.py"],
    [sys.executable, "benchmarks/benchmark_kernel.py", "--iterations", "1000"],
    [sys.executable, "benchmarks/benchmark_suite.py", "--iterations", "1000"],
    [sys.executable, "-m", "unittest", "discover", "-s", "thirsty-ai-builder/backend/tests", "-p", "test_backend.py"],
]


def main() -> int:
    for command in COMMANDS:
        print(f"RUN: {' '.join(command)}")
        completed = subprocess.run(command, cwd=ROOT, check=False)
        if completed.returncode != 0:
            print(f"FAIL: {' '.join(command)} exited {completed.returncode}")
            return completed.returncode
    print("PASS: full local verification gate completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
