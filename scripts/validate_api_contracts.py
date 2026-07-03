from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_PATHS = {
    "/health",
    "/v1/execute",
    "/v1/replay",
    "/v1/audit",
    "/v1/audit/stream",
    "/v1/query",
    "/v1/grpc",
}
PYTHON_METHODS = ["def health", "def replay", "def audit", "def query", "def grpc_compat", "def execute"]
TYPESCRIPT_METHODS = ["health()", "replay()", "audit()", "query(query: string)", "grpcCompat", "execute(request: ExecuteRequest)"]
POWERSHELL_METHODS = [
    "Invoke-BuilderHealth",
    "Invoke-BuilderReplay",
    "Invoke-BuilderAudit",
    "Invoke-BuilderExecute",
    "Invoke-BuilderQuery",
    "Invoke-BuilderGrpcCompat",
]
PROTO_TOKENS = ["service BuilderService", "rpc Execute", "rpc Replay", "message ExecuteRequest"]


def main() -> int:
    failures: list[str] = []
    openapi = json.loads((ROOT / "docs" / "api" / "openapi.json").read_text(encoding="utf-8"))
    paths = set(openapi.get("paths", {}))
    missing_paths = REQUIRED_PATHS - paths
    if missing_paths:
        failures.append(f"openapi missing paths: {sorted(missing_paths)}")

    python_client = (ROOT / "sdk" / "python" / "constitutional_builder_sdk" / "client.py").read_text(
        encoding="utf-8"
    )
    for token in PYTHON_METHODS:
        if token not in python_client:
            failures.append(f"python sdk missing {token}")

    typescript_client = (ROOT / "sdk" / "typescript" / "client.ts").read_text(encoding="utf-8")
    for token in TYPESCRIPT_METHODS:
        if token not in typescript_client:
            failures.append(f"typescript sdk missing {token}")

    powershell_client = (ROOT / "sdk" / "powershell" / "BuilderClient.psm1").read_text(encoding="utf-8")
    for token in POWERSHELL_METHODS:
        if token not in powershell_client:
            failures.append(f"powershell sdk missing {token}")

    proto = (ROOT / "proto" / "constitutional_builder" / "v1" / "builder.proto").read_text(
        encoding="utf-8"
    )
    for token in PROTO_TOKENS:
        if token not in proto:
            failures.append(f"proto missing {token}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    print("PASS: API and SDK contracts validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
