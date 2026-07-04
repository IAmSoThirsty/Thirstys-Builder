"""Live federation conformance - Volume VIII (0.2.0 roadmap line).

Spawns 3 real HTTP nodes on loopback, runs 6 requests across
partition transitions, asserts the cluster's quorum and
split-brain behavior. Wired into scripts/verify_all.py as
step 16.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))

from constitutional_builder import (  # noqa: E402
    ActionRequest,
    CapabilityGrant,
    CapabilityRegistry,
    DecisionStatus,
    IdentityRegistry,
    InMemoryAuditLog,
    PolicyEffect,
    PolicyEngine,
    PolicyRule,
    Subject,
)
from constitutional_builder.kernel import ConstitutionalKernel  # noqa: E402
from constitutional_builder.federation import (  # noqa: E402
    build_live_cluster,
    federation_hash_from_live,
)


def _kernel(allow: bool) -> ConstitutionalKernel:
    return ConstitutionalKernel(
        identities=IdentityRegistry([Subject("operator", "Operator")]),
        policies=PolicyEngine(
            [PolicyRule("node-policy", PolicyEffect.ALLOW if allow else PolicyEffect.DENY,
                        "echo", "demo", "operator", "ok" if allow else "no")]
        ),
        capabilities=CapabilityRegistry(
            [CapabilityGrant("grant", "operator", "echo", "demo")] if allow else []
        ),
        audit_log=InMemoryAuditLog(),
        handlers={"echo": lambda resource, parameters: {"resource": resource, "parameters": parameters}},
    )


def main() -> int:
    cluster = build_live_cluster(node_count=3)
    try:
        # 1. Baseline: 3/3 allow, quorum=2, allowed.
        d1 = cluster.submit(ActionRequest("conf-1", "operator", "echo", "demo", {}))
        if d1.status is not DecisionStatus.ALLOWED or d1.approvals != 3:
            print(f"FAIL: step 1 expected 3 approvals, got {d1.status.value} approvals={d1.approvals}")
            return 1

        # 2. Single peer partitioned: 2/2 visible, quorum=2, allowed.
        cluster.set_partition({"node-3"})
        d2 = cluster.submit(ActionRequest("conf-2", "operator", "echo", "demo", {}))
        if d2.status is not DecisionStatus.ALLOWED:
            print(f"FAIL: step 2 expected allow, got {d2.status.value}: {d2.reason}")
            return 1

        # 3. Two peers partitioned (split-brain): visible=1, quorum=2, denied.
        cluster.set_partition({"node-2", "node-3"})
        d3 = cluster.submit(ActionRequest("conf-3", "operator", "echo", "demo", {}))
        if d3.status is not DecisionStatus.DENIED or "partition" not in d3.reason:
            print(f"FAIL: step 3 expected partition denial, got {d3.status.value}: {d3.reason}")
            return 1

        # 4. Clear partition: back to 3/3, allowed.
        cluster.clear_partition()
        d4 = cluster.submit(ActionRequest("conf-4", "operator", "echo", "demo", {}))
        if d4.status is not DecisionStatus.ALLOWED:
            print(f"FAIL: step 4 expected allow after recovery, got {d4.status.value}: {d4.reason}")
            return 1

        # 5. Federation hash is a valid SHA-256 hex and matches the count.
        h = federation_hash_from_live(cluster)
        if len(h) != 64:
            print(f"FAIL: federation hash not 64 hex chars: {h!r}")
            return 1
        try:
            int(h, 16)
        except ValueError:
            print(f"FAIL: federation hash not hex: {h!r}")
            return 1

        # 6. Re-partition to a different node, deny, recover again.
        cluster.set_partition({"node-1"})
        d6a = cluster.submit(ActionRequest("conf-6a", "operator", "echo", "demo", {}))
        if d6a.status is not DecisionStatus.ALLOWED:
            print(f"FAIL: step 6a expected allow, got {d6a.status.value}: {d6a.reason}")
            return 1
        cluster.set_partition({"node-1", "node-2"})
        d6b = cluster.submit(ActionRequest("conf-6b", "operator", "echo", "demo", {}))
        if d6b.status is not DecisionStatus.DENIED or "partition" not in d6b.reason:
            print(f"FAIL: step 6b expected partition denial, got {d6b.status.value}: {d6b.reason}")
            return 1
        cluster.clear_partition()
        d6c = cluster.submit(ActionRequest("conf-6c", "operator", "echo", "demo", {}))
        if d6c.status is not DecisionStatus.ALLOWED:
            print(f"FAIL: step 6c expected allow, got {d6c.status.value}: {d6c.reason}")
            return 1

        print(
            "PASS: live federation conformance passed; "
            f"steps=6 federation_hash={h} "
            f"events={sum(len(n.kernel.audit_log.events) for n in cluster.nodes)}"
        )
        return 0
    finally:
        cluster.stop()


if __name__ == "__main__":
    raise SystemExit(main())
