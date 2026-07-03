from __future__ import annotations

import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))

from constitutional_builder import (  # noqa: E402
    ActionRequest,
    CapabilityGrant,
    CapabilityRegistry,
    ConstitutionalKernel,
    DecisionStatus,
    IdentityRegistry,
    InMemoryAuditLog,
    PolicyEffect,
    PolicyEngine,
    PolicyRule,
    ReplayVerifier,
    Subject,
)


def main() -> int:
    rng = random.Random(20260703)
    calls: list[str] = []
    kernel = ConstitutionalKernel(
        identities=IdentityRegistry([Subject("operator", "Operator"), Subject("disabled", "Disabled", active=False)]),
        policies=PolicyEngine(
            [
                PolicyRule("allow-echo", PolicyEffect.ALLOW, "echo", "demo", "operator"),
                PolicyRule("deny-delete", PolicyEffect.DENY, "delete", "*", "*", "delete blocked"),
            ]
        ),
        capabilities=CapabilityRegistry([CapabilityGrant("grant-echo", "operator", "echo", "demo")]),
        audit_log=InMemoryAuditLog(),
        handlers={"echo": lambda resource, parameters: calls.append(resource) or {"ok": True}},
    )

    allowed_count = 0
    denied_count = 0
    for index in range(250):
        request = ActionRequest(
            request_id=f"fuzz-{index}",
            subject_id=rng.choice(["operator", "unknown", "disabled"]),
            operation=rng.choice(["echo", "delete", "missing_handler"]),
            resource=rng.choice(["demo", "other"]),
            parameters={"seed": index},
        )
        before_calls = len(calls)
        decision = kernel.handle(request)
        if decision.status is DecisionStatus.ALLOWED:
            allowed_count += 1
            if request.subject_id != "operator" or request.operation != "echo" or request.resource != "demo":
                print(f"FAIL: unauthorized request allowed: {request}")
                return 1
        else:
            denied_count += 1
            if len(calls) != before_calls:
                print(f"FAIL: denied request executed handler: {request}")
                return 1

    replay = ReplayVerifier().verify(kernel.audit_log.events)
    if not replay.valid:
        print(f"FAIL: replay invalid after fuzz: {replay.reason}")
        return 1
    print(f"PASS: fuzz authorization passed; allowed={allowed_count} denied={denied_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
