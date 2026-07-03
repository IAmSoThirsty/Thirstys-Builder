from __future__ import annotations

import sys
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
    Subject,
)


def main() -> int:
    cluster = QuorumCluster(
        [
            BuilderNode("node-1", _kernel(allow=True)),
            BuilderNode("node-2", _kernel(allow=True)),
            BuilderNode("node-3", _kernel(allow=False)),
        ],
        quorum=2,
    )
    decision = cluster.submit(ActionRequest("cluster-conf-1", "operator", "echo", "demo", {}))
    if decision.status is not DecisionStatus.ALLOWED:
        print(f"FAIL: expected cluster allow, got {decision.status.value}: {decision.reason}")
        return 1
    report = FederationVerifier().verify(cluster.nodes)
    if not report.valid:
        print(f"FAIL: federation verification failed: {report.reason}")
        return 1
    print(
        "PASS: cluster conformance passed; "
        f"approvals={decision.approvals} denials={decision.denials} "
        f"events={report.event_count} federation_hash={report.federation_hash}"
    )
    return 0


def _kernel(*, allow: bool) -> ConstitutionalKernel:
    return ConstitutionalKernel(
        identities=IdentityRegistry([Subject("operator", "Operator")]),
        policies=PolicyEngine(
            [
                PolicyRule(
                    "node-policy",
                    PolicyEffect.ALLOW if allow else PolicyEffect.DENY,
                    "echo",
                    "demo",
                    "operator",
                    "node allows" if allow else "node denies",
                )
            ]
        ),
        capabilities=CapabilityRegistry([CapabilityGrant("grant", "operator", "echo", "demo")]),
        audit_log=InMemoryAuditLog(),
        handlers={"echo": lambda resource, parameters: {"resource": resource, "parameters": parameters}},
    )


if __name__ == "__main__":
    raise SystemExit(main())
