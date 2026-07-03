from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))

from constitutional_builder import (  # noqa: E402
    ActionRequest,
    BuilderNode,
    CapabilityGrant,
    CapabilityRegistry,
    ConstitutionalKernel,
    DecisionStatus,
    FederationVerifier,
    IdentityRegistry,
    InMemoryAuditLog,
    PolicyEffect,
    PolicyEngine,
    PolicyRule,
    QuorumCluster,
    ReplayVerifier,
    Subject,
)


def main() -> int:
    checks = [
        handler_failure_is_audited,
        audit_tamper_is_detected,
        cluster_quorum_loss_denies,
        federation_tamper_is_detected,
    ]
    for check in checks:
        result = check()
        if result is not None:
            print(f"FAIL: {result}")
            return 1
    print(f"PASS: {len(checks)} chaos checks passed")
    return 0


def handler_failure_is_audited() -> str | None:
    kernel = _kernel(handler=lambda _resource, _parameters: (_ for _ in ()).throw(RuntimeError("boom")))
    decision = kernel.handle(ActionRequest("chaos-handler", "operator", "echo", "demo", {}))
    if decision.status is not DecisionStatus.FAILED:
        return f"handler failure returned {decision.status.value}"
    if not kernel.audit_log.verify():
        return "audit chain invalid after handler failure"
    return None


def audit_tamper_is_detected() -> str | None:
    audit = InMemoryAuditLog()
    event = audit.append(
        request_id="chaos-audit",
        subject_id="operator",
        operation="echo",
        resource="demo",
        status="allowed",
        reason="ok",
        metadata={},
    )
    report = ReplayVerifier().verify((replace(event, reason="tampered"),))
    if report.valid:
        return "tampered audit event verified"
    return None


def cluster_quorum_loss_denies() -> str | None:
    cluster = QuorumCluster(
        [
            BuilderNode("node-1", _kernel(allow=True)),
            BuilderNode("node-2", _kernel(allow=False)),
            BuilderNode("node-3", _kernel(allow=False)),
        ],
        quorum=2,
    )
    decision = cluster.submit(ActionRequest("chaos-cluster", "operator", "echo", "demo", {}))
    if decision.status is not DecisionStatus.DENIED:
        return "cluster quorum loss did not deny"
    return None


def federation_tamper_is_detected() -> str | None:
    good = BuilderNode("node-1", _kernel(allow=True))
    good.handle(ActionRequest("chaos-fed", "operator", "echo", "demo", {}))
    tampered_event = replace(good.kernel.audit_log.events[0], reason="tampered")
    bad_log = InMemoryAuditLog()
    bad_log._events.append(tampered_event)  # noqa: SLF001 - intentional corruption fixture.
    bad = BuilderNode("node-2", _kernel(allow=True, audit_log=bad_log))
    report = FederationVerifier().verify((good, bad))
    if report.valid:
        return "federation verifier accepted tampered node"
    return None


def _kernel(*, allow: bool = True, handler=None, audit_log=None) -> ConstitutionalKernel:
    return ConstitutionalKernel(
        identities=IdentityRegistry([Subject("operator", "Operator")]),
        policies=PolicyEngine(
            [
                PolicyRule(
                    "policy",
                    PolicyEffect.ALLOW if allow else PolicyEffect.DENY,
                    "echo",
                    "demo",
                    "operator",
                    "allow" if allow else "deny",
                )
            ]
        ),
        capabilities=CapabilityRegistry([CapabilityGrant("grant", "operator", "echo", "demo")]),
        audit_log=audit_log or InMemoryAuditLog(),
        handlers={"echo": handler or (lambda resource, parameters: {"resource": resource, "parameters": parameters})},
    )


if __name__ == "__main__":
    raise SystemExit(main())
