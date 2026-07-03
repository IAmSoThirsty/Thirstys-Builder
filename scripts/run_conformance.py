from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))

from constitutional_builder.config import build_kernel_from_config, load_config  # noqa: E402
from constitutional_builder.models import ActionRequest  # noqa: E402
from constitutional_builder.replay import ReplayVerifier  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run JSON conformance scenarios.")
    parser.add_argument("--suite", default=str(ROOT / "examples" / "conformance-suite.json"))
    args = parser.parse_args()

    suite_path = Path(args.suite).resolve()
    suite = json.loads(suite_path.read_text(encoding="utf-8"))
    config_path = (suite_path.parent / suite["config"]).resolve()
    kernel = build_kernel_from_config(load_config(config_path))

    failures: list[str] = []
    for scenario in suite["scenarios"]:
        request_data = _load_request(suite_path.parent, scenario)
        decision = kernel.handle(ActionRequest(**request_data))
        expected_status = scenario["expected_status"]
        if decision.status.value != expected_status:
            failures.append(
                f"{scenario['name']}: expected {expected_status}, got {decision.status.value}"
            )
        expected_reason = scenario.get("expected_reason")
        if expected_reason and decision.reason != expected_reason:
            failures.append(
                f"{scenario['name']}: expected reason {expected_reason!r}, got {decision.reason!r}"
            )

    replay = ReplayVerifier().verify(kernel.audit_log.events)
    if not replay.valid:
        failures.append(f"replay failed: {replay.reason}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    print(f"PASS: {len(suite['scenarios'])} conformance scenarios passed; replay verified")
    return 0


def _load_request(suite_dir: Path, scenario: dict[str, object]) -> dict[str, object]:
    if "inline_request" in scenario:
        return dict(scenario["inline_request"])  # type: ignore[arg-type]
    request_path = suite_dir / str(scenario["request"])
    return json.loads(request_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    raise SystemExit(main())
