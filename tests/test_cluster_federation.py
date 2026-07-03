import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "source"))

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


def make_kernel(*, allow: bool) -> ConstitutionalKernel:
    effect = PolicyEffect.ALLOW if allow else PolicyEffect.DENY
    reason = "allowed by node policy" if allow else "denied by node policy"
    return ConstitutionalKernel(
        identities=IdentityRegistry([Subject("operator", "Operator")]),
        policies=PolicyEngine([PolicyRule("policy", effect, "echo", "demo", "operator", reason)]),
        capabilities=CapabilityRegistry([CapabilityGrant("grant", "operator", "echo", "demo")]),
        audit_log=InMemoryAuditLog(),
        handlers={"echo": lambda resource, parameters: {"resource": resource, "parameters": parameters}},
    )


class ClusterFederationTests(unittest.TestCase):
    def test_cluster_allows_when_quorum_approves(self):
        cluster = QuorumCluster(
            [
                BuilderNode("node-1", make_kernel(allow=True)),
                BuilderNode("node-2", make_kernel(allow=True)),
                BuilderNode("node-3", make_kernel(allow=False)),
            ],
            quorum=2,
        )

        decision = cluster.submit(ActionRequest("req-1", "operator", "echo", "demo", {}))

        self.assertEqual(decision.status, DecisionStatus.ALLOWED)
        self.assertEqual(decision.approvals, 2)
        self.assertEqual(decision.denials, 1)
        report = FederationVerifier().verify(cluster.nodes)
        self.assertTrue(report.valid)
        self.assertEqual(report.event_count, 3)
        self.assertEqual(len(report.federation_hash), 64)

    def test_cluster_denies_when_quorum_missing(self):
        cluster = QuorumCluster(
            [
                BuilderNode("node-1", make_kernel(allow=True)),
                BuilderNode("node-2", make_kernel(allow=False)),
                BuilderNode("node-3", make_kernel(allow=False)),
            ],
            quorum=2,
        )

        decision = cluster.submit(ActionRequest("req-1", "operator", "echo", "demo", {}))

        self.assertEqual(decision.status, DecisionStatus.DENIED)
        self.assertEqual(decision.reason, "cluster quorum not reached")
        self.assertEqual(decision.approvals, 1)


if __name__ == "__main__":
    unittest.main()
