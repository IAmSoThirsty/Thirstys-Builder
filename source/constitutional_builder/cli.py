from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from .audit import InMemoryAuditLog
from .capability import CapabilityGrant, CapabilityRegistry
from .identity import IdentityRegistry, Subject
from .kernel import ConstitutionalKernel
from .models import ActionRequest
from .policy import PolicyEffect, PolicyEngine, PolicyRule
from .replay import ReplayVerifier


def _echo_handler(resource: str, parameters: dict[str, object]) -> dict[str, object]:
    return {"resource": resource, "parameters": parameters}


def build_demo_kernel() -> ConstitutionalKernel:
    return ConstitutionalKernel(
        identities=IdentityRegistry([Subject("operator", "Demo Operator", ("admin",))]),
        policies=PolicyEngine(
            [
                PolicyRule(
                    policy_id="policy-demo-allow-echo",
                    effect=PolicyEffect.ALLOW,
                    subject_id="operator",
                    operation="echo",
                    resource="demo",
                    reason="demo echo is allowed",
                )
            ]
        ),
        capabilities=CapabilityRegistry(
            [CapabilityGrant("grant-demo-echo", "operator", "echo", "demo")]
        ),
        audit_log=InMemoryAuditLog(),
        handlers={"echo": _echo_handler},
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a governed demo request.")
    parser.add_argument("--subject", default="operator")
    parser.add_argument("--operation", default="echo")
    parser.add_argument("--resource", default="demo")
    parser.add_argument("--request-id", default="demo-1")
    args = parser.parse_args()

    kernel = build_demo_kernel()
    decision = kernel.handle(
        ActionRequest(
            request_id=args.request_id,
            subject_id=args.subject,
            operation=args.operation,
            resource=args.resource,
            parameters={"source": "cli"},
        )
    )
    replay = ReplayVerifier().verify(kernel.audit_log.events)
    print(json.dumps({"decision": asdict(decision), "replay": asdict(replay)}, indent=2, default=str))
    return 0 if decision.allowed and replay.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
