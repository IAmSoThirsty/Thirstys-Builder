import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "source"))

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


def echo_handler(resource, parameters):
    return {"resource": resource, "parameters": parameters}


class VerticalSliceTests(unittest.TestCase):
    def build_kernel(self):
        return ConstitutionalKernel(
            identities=IdentityRegistry([Subject("alice", "Alice", ("operator",))]),
            policies=PolicyEngine(
                [
                    PolicyRule(
                        policy_id="policy-allow-echo",
                        effect=PolicyEffect.ALLOW,
                        subject_id="alice",
                        operation="echo",
                        resource="safe-resource",
                    )
                ]
            ),
            capabilities=CapabilityRegistry(
                [CapabilityGrant("grant-echo", "alice", "echo", "safe-resource")]
            ),
            audit_log=InMemoryAuditLog(),
            handlers={"echo": echo_handler},
        )

    def test_allowed_request_executes_and_audits(self):
        kernel = self.build_kernel()

        decision = kernel.handle(
            ActionRequest(
                request_id="req-1",
                subject_id="alice",
                operation="echo",
                resource="safe-resource",
                parameters={"message": "hello"},
            )
        )

        self.assertEqual(decision.status, DecisionStatus.ALLOWED)
        self.assertEqual(decision.result.output["parameters"]["message"], "hello")
        self.assertEqual(len(kernel.audit_log.events), 1)
        self.assertTrue(kernel.audit_log.verify())

    def test_replay_verifies_hash_chain(self):
        kernel = self.build_kernel()
        kernel.handle(ActionRequest("req-1", "alice", "echo", "safe-resource", {}))
        report = ReplayVerifier().verify(kernel.audit_log.events)
        self.assertTrue(report.valid)
        self.assertEqual(report.event_count, 1)


if __name__ == "__main__":
    unittest.main()
