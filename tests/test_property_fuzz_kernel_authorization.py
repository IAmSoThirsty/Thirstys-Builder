from __future__ import annotations

import random
import unittest
from pathlib import Path
import sys

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


SUBJECTS = (
    Subject("operator", "Operator"),
    Subject("auditor", "Auditor"),
    Subject("disabled", "Disabled", active=False),
    Subject("unknown_never_in_registry", "Unknown"),
)

OPERATIONS = ("echo", "delete", "rotate", "missing_handler", "explode", "")
RESOURCES = ("demo", "prod", "audit", "config", "")

POLICIES = (
    PolicyRule("allow-echo-demo", PolicyEffect.ALLOW, "echo", "demo", "operator"),
    PolicyRule("allow-rotate-config", PolicyEffect.ALLOW, "rotate", "config", "auditor"),
    PolicyRule("deny-delete-prod", PolicyEffect.DENY, "delete", "prod", "*", "delete blocked"),
    PolicyRule("deny-explode", PolicyEffect.DENY, "explode", "*", "*", "explode blocked"),
    PolicyRule("allow-echo-wildcard", PolicyEffect.ALLOW, "echo", "*", "auditor"),
)

GRANTS = (
    CapabilityGrant("grant-echo-demo", "operator", "echo", "demo"),
    CapabilityGrant("grant-rotate-config", "auditor", "rotate", "config"),
)


class _CountingHandler:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def make(self, op: str):
        def _h(resource: str, parameters):
            self.calls.append((op, resource))
            return {"ok": True, "echoed": resource, "params": dict(parameters)}

        return _h


def _build_kernel():
    counter = _CountingHandler()
    handlers = {
        "echo": counter.make("echo"),
        "delete": counter.make("delete"),
        "rotate": counter.make("rotate"),
    }
    kernel = ConstitutionalKernel(
        identities=IdentityRegistry(list(SUBJECTS)),
        policies=PolicyEngine(list(POLICIES)),
        capabilities=CapabilityRegistry(list(GRANTS)),
        audit_log=InMemoryAuditLog(),
        handlers=handlers,
    )
    return kernel, counter


def _oracle(request: ActionRequest, handlers: dict) -> bool:
    if not request.request_id or not request.subject_id or not request.operation or not request.resource:
        return False
    if request.subject_id not in {s.subject_id for s in SUBJECTS if s.active}:
        return False
    matching = [rule for rule in POLICIES if rule.matches(request)]
    if any(rule.effect is PolicyEffect.DENY for rule in matching):
        return False
    if not any(rule.effect is PolicyEffect.ALLOW for rule in matching):
        return False
    if not any(grant.matches(request) for grant in GRANTS):
        return False
    if request.operation not in handlers:
        return False
    return True


class PropertyFuzzKernelAuthorization(unittest.TestCase):
    """Property-based invariants over the kernel authorization surface.

    Smaller run than scripts/property_fuzz_kernel_authorization.py so the
    unittest gate stays fast, but enough iterations to exercise every
    invariant on every code path.
    """

    def test_invariants_hold_over_random_requests(self) -> None:
        iterations = 500
        kernel, counter = _build_kernel()
        rng = random.Random(20260703)

        for index in range(iterations):
            request = ActionRequest(
                request_id=f"t-{index}",
                subject_id=rng.choice([s.subject_id for s in SUBJECTS]),
                operation=rng.choice(OPERATIONS),
                resource=rng.choice(RESOURCES),
                parameters={"seed": index},
            )
            calls_before = len(counter.calls)
            decision = kernel.handle(request)
            oracle = _request_allow_oracle = _oracle(request, kernel.handlers)

            # Invariant: parameter-independence. Mutate parameters and assert
            # the three authorization layers produce identical decisions.
            twin = ActionRequest(
                request_id=request.request_id,
                subject_id=request.subject_id,
                operation=request.operation,
                resource=request.resource,
                parameters={"variant": index},
            )
            self.assertEqual(
                kernel.identities.resolve(request.subject_id),
                kernel.identities.resolve(twin.subject_id),
                f"identity resolution is parameter-dependent at {index}",
            )
            self.assertEqual(
                kernel.policies.evaluate(request),
                kernel.policies.evaluate(twin),
                f"policy is parameter-dependent at {index}",
            )
            self.assertEqual(
                kernel.capabilities.check(request),
                kernel.capabilities.check(twin),
                f"capability is parameter-dependent at {index}",
            )

            # Invariant: allow-iff-triple-match.
            self.assertEqual(
                decision.allowed,
                oracle,
                f"decision.allowed={decision.allowed} oracle={oracle} at {index} "
                f"subj={request.subject_id} op={request.operation} res={request.resource} "
                f"reason={decision.reason!r}",
            )

            # Invariant: no-execute-on-deny.
            if decision.status is not DecisionStatus.ALLOWED:
                self.assertEqual(
                    len(counter.calls),
                    calls_before,
                    f"denied/failed request executed handler at {index}: {request}",
                )
            else:
                new_calls = counter.calls[calls_before:]
                expected = (request.operation, request.resource)
                self.assertIn(
                    expected,
                    new_calls,
                    f"allowed request did not invoke expected handler at {index}: {request} "
                    f"new_calls={new_calls} reason={decision.reason!r}",
                )

            # Invariant: every decision produces an audit event id.
            self.assertTrue(
                decision.audit_event_id,
                f"decision missing audit_event_id at {index}: {request}",
            )

        # Invariant: full audit chain is replay valid.
        replay = ReplayVerifier().verify(kernel.audit_log.events)
        self.assertTrue(
            replay.valid,
            f"replay invalid after property fuzz: {replay.reason}",
        )
        self.assertEqual(
            len(kernel.audit_log.events),
            iterations,
            "audit event count must equal decision count",
        )


if __name__ == "__main__":
    raise SystemExit(unittest.main())
