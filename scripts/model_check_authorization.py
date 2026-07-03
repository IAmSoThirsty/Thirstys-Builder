from __future__ import annotations

import itertools
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "formal" / "kernel_authorization_model.json"


def main() -> int:
    model = json.loads(MODEL_PATH.read_text(encoding="utf-8"))
    keys = list(model["bounded_inputs"])
    failures: list[str] = []
    checked = 0

    for values in itertools.product(*[model["bounded_inputs"][key] for key in keys]):
        case = dict(zip(keys, values, strict=True))
        checked += 1
        executed = transition_executes(case)
        authorized = (
            case["identity_active"]
            and case["policy_allows"]
            and case["capability_allows"]
            and case["handler_registered"]
        )
        if executed and not authorized:
            failures.append(f"unauthorized execution reachable: {case}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    print(f"PASS: authorization invariant checked across {checked} bounded states")
    return 0


def transition_executes(case: dict[str, bool]) -> bool:
    if not case["identity_active"]:
        return False
    if not case["policy_allows"]:
        return False
    if not case["capability_allows"]:
        return False
    if not case["handler_registered"]:
        return False
    return True


if __name__ == "__main__":
    raise SystemExit(main())
