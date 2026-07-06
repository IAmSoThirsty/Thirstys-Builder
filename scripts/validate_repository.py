from __future__ import annotations

import json
from pathlib import Path

try:
    from .release_config import PACKAGE_NAME
except ImportError:  # pragma: no cover - direct script execution
    from release_config import PACKAGE_NAME


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_DIRS = [
    "source",
    "spec",
    "tests",
    "benchmarks",
    "sdk",
    "proto",
    "examples",
    "deploy",
    "formal",
    "security",
    "ci",
    "docs",
    "commander",
]
REQUIRED_FILES = [
    ".gitignore",
    "README.md",
    "AGENTS.md",
    "pyproject.toml",
    "spec/requirements.json",
    "docs/architecture.md",
    "docs/api/openapi.json",
    "proto/constitutional_builder/v1/builder.proto",
    "docs/operations/runbook.md",
    "security/threat-model.md",
    "formal/proof-obligations.md",
    "commander/audit-log.md",
    "commander/final-certification-report.md",
    "deploy/Dockerfile",
    "deploy/docker-compose.yml",
    "deploy/kubernetes.yaml",
    "deploy/example-config.json",
    "examples/conformance-suite.json",
    "examples/policy-bundle.json",
    "scripts/run_conformance.py",
    "scripts/run_grpc_conformance.py",
    "scripts/run_cluster_conformance.py",
    "scripts/model_check_authorization.py",
    "scripts/validate_formal_models.py",
    "scripts/install_formal_tools.py",
    "tools/formal-tools.lock.json",
    "scripts/validate_api_contracts.py",
    "scripts/fuzz_kernel_authorization.py",
    "scripts/run_chaos_checks.py",
    "scripts/generate_release_evidence.py",
    "scripts/build_release_package.py",
    "scripts/sign_release_package.py",
    "scripts/validate_deployment.py",
    "scripts/verify_all.py",
    "source/constitutional_builder/grpc_server.py",
    "source/constitutional_builder/v1/builder_pb2.py",
    "source/constitutional_builder/v1/builder_pb2_grpc.py",
    "source/constitutional_builder/v1/__init__.py",
    "ci/github-actions.yml",
    "formal/kernel_authorization_model.json",
    "formal/authorization_invariant.tla",
    "formal/policy_authorization.als",
    "tools/formal-tools.lock.json",
    "release/sbom.json",
    "release/provenance.json",
    "release/provenance.signature.json",
    "release/package-manifest.json",
    f"release/{PACKAGE_NAME}",
    "release/package-signature.json",
    "release/signing-public-key.pem",
]
REQUIRED_REQUIREMENT_KEYS = {
    "id",
    "statement",
    "implementation",
    "tests",
    "benchmarks",
    "metrics",
    "formal",
    "docs",
    "security",
    "operations",
}


def main() -> int:
    failures: list[str] = []

    for directory in REQUIRED_DIRS:
        if not (ROOT / directory).is_dir():
            failures.append(f"missing required directory: {directory}")

    for file_path in REQUIRED_FILES:
        if not (ROOT / file_path).is_file():
            failures.append(f"missing required file: {file_path}")

    for number in range(0, 18):
        matches = sorted((ROOT / "spec").glob(f"volume-{number:02d}-*.md"))
        if not matches:
            failures.append(f"missing spec volume {number:02d}")

    requirements_path = ROOT / "spec" / "requirements.json"
    if requirements_path.exists():
        data = json.loads(requirements_path.read_text(encoding="utf-8"))
        for requirement in data.get("requirements", []):
            missing = REQUIRED_REQUIREMENT_KEYS - set(requirement)
            if missing:
                failures.append(f"{requirement.get('id', '<unknown>')} missing keys: {sorted(missing)}")
            for key in REQUIRED_REQUIREMENT_KEYS - {"id", "statement", "metrics"}:
                for referenced in requirement.get(key, []):
                    anchorless = referenced.split("#", 1)[0]
                    if anchorless and not (ROOT / anchorless).exists():
                        failures.append(f"{requirement['id']} references missing {key}: {referenced}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    print("PASS: repository structure and traceability validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
