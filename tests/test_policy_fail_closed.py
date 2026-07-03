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
    Subject,
)


class FailClosedTests(unittest.TestCase):
    def test_no_matching_policy_denies_without_execution(self):
        calls = []

        def handler(resource, parameters):
            calls.append((resource, parameters))
            return {"ok": True}

        kernel = ConstitutionalKernel(
            identities=IdentityRegistry([Subject("alice", "Alice")]),
            policies=PolicyEngine([]),
            capabilities=CapabilityRegistry([CapabilityGrant("grant", "alice", "echo", "*")]),
            audit_log=InMemoryAuditLog(),
            handlers={"echo": handler},
        )

        decision = kernel.handle(ActionRequest("req-1", "alice", "echo", "resource", {}))

        self.assertEqual(decision.status, DecisionStatus.DENIED)
        self.assertEqual(calls, [])
        self.assertEqual(kernel.audit_log.events[0].reason, "no matching policy")

    def test_explicit_deny_overrides_allow(self):
        kernel = ConstitutionalKernel(
            identities=IdentityRegistry([Subject("alice", "Alice")]),
            policies=PolicyEngine(
                [
                    PolicyRule("allow", PolicyEffect.ALLOW, "echo", "*", "alice"),
                    PolicyRule("deny", PolicyEffect.DENY, "echo", "*", "alice", "blocked"),
                ]
            ),
            capabilities=CapabilityRegistry([CapabilityGrant("grant", "alice", "echo", "*")]),
            audit_log=InMemoryAuditLog(),
            handlers={"echo": lambda _resource, _parameters: {"ok": True}},
        )

        decision = kernel.handle(ActionRequest("req-1", "alice", "echo", "resource", {}))

        self.assertEqual(decision.status, DecisionStatus.DENIED)
        self.assertEqual(decision.reason, "blocked")

    def test_missing_capability_denies_without_execution(self):
        calls = []
        kernel = ConstitutionalKernel(
            identities=IdentityRegistry([Subject("alice", "Alice")]),
            policies=PolicyEngine([PolicyRule("allow", PolicyEffect.ALLOW, "echo", "*", "alice")]),
            capabilities=CapabilityRegistry([]),
            audit_log=InMemoryAuditLog(),
            handlers={"echo": lambda _resource, _parameters: calls.append("called")},
        )

        decision = kernel.handle(ActionRequest("req-1", "alice", "echo", "resource", {}))

        self.assertEqual(decision.status, DecisionStatus.DENIED)
        self.assertEqual(calls, [])
        self.assertEqual(decision.reason, "no matching capability grant")


if __name__ == "__main__":
    unittest.main()
