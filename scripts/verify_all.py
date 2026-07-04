from __future__ import annotations

import subprocess
import sys
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


FRONTEND = ROOT / "thirsty-ai-builder" / "frontend"
RUST_AUDITOR = ROOT / "thirsty-ai-builder" / "rust-auditor"
NPM = "npm.cmd" if os.name == "nt" else "npm"
CARGO = "cargo.exe" if os.name == "nt" else "cargo"


COMMANDS = [
    {"argv": [sys.executable, "-m", "compileall", "-q", "source", "tests", "scripts", "benchmarks"]},
    {"argv": [sys.executable, "-m", "unittest", "discover", "-s", "tests"]},
    {"argv": [sys.executable, "scripts/validate_repository.py"]},
    {"argv": [sys.executable, "scripts/validate_api_contracts.py"]},
    {"argv": [sys.executable, "scripts/model_check_authorization.py"]},
    {"argv": [sys.executable, "scripts/install_formal_tools.py"]},
    {"argv": [sys.executable, "scripts/validate_formal_models.py"]},
    {"argv": [sys.executable, "scripts/fuzz_kernel_authorization.py"]},
    {"argv": [sys.executable, "scripts/property_fuzz_kernel_authorization.py"]},
    {"argv": [sys.executable, "scripts/run_conformance.py"]},
    {"argv": [sys.executable, "scripts/run_grpc_conformance.py"]},
    {"argv": [sys.executable, "scripts/run_cluster_conformance.py"]},
    {"argv": [sys.executable, "scripts/run_live_federation_conformance.py"]},
    {"argv": [sys.executable, "scripts/run_chaos_checks.py"]},
    {"argv": [sys.executable, "scripts/build_personal_builder_coder.py", "--check"]},
    {"argv": [sys.executable, "scripts/generate_release_evidence.py", "--check"]},
    {"argv": [sys.executable, "scripts/build_release_package.py", "--check"]},
    {"argv": [sys.executable, "scripts/sign_release_package.py", "--check"]},
    {"argv": [sys.executable, "scripts/validate_deployment.py"]},
    {"argv": [sys.executable, "scripts/validate_thirsty_ai_builder_deployment.py"]},
    {"argv": [sys.executable, "scripts/verify_audit_chain.py"]},
    {"argv": [sys.executable, "benchmarks/benchmark_kernel.py", "--iterations", "1000"]},
    {"argv": [sys.executable, "benchmarks/benchmark_suite.py", "--iterations", "1000"]},
    {"argv": [sys.executable, "-m", "unittest", "discover", "-s", "thirsty-ai-builder/backend/tests"]},
    {
        "argv": [NPM, "test", "--", "--watchAll=false", "--passWithNoTests"],
        "cwd": FRONTEND,
        "env": {"CI": "true"},
    },
    {"argv": [NPM, "run", "build"], "cwd": FRONTEND},
    {
        "argv": [CARGO, "+stable-x86_64-pc-windows-gnu", "test"],
        "cwd": RUST_AUDITOR,
        "env": {"CARGO_TARGET_X86_64_PC_WINDOWS_GNU_LINKER": "rust-lld"},
    },
]


def main() -> int:
    for spec in COMMANDS:
        command = spec["argv"]
        cwd = spec.get("cwd", ROOT)
        env = os.environ.copy()
        env.update(spec.get("env", {}))
        print(f"RUN ({cwd}): {' '.join(command)}")
        completed = subprocess.run(command, cwd=cwd, env=env, check=False)
        if completed.returncode != 0:
            print(f"FAIL: {' '.join(command)} exited {completed.returncode}")
            return completed.returncode
    print("PASS: full local verification gate completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
