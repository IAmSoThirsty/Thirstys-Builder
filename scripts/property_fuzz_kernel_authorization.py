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


# Property-based fuzz. Generates a wide random request space and asserts four
# invariants on every iteration. No new dependencies. The seed is fixed so the
# run is deterministic; CI failure means there is a real authorization bug.
#
# Invariants:
#   1. Parameter-independence: the decision (allowed/denied/failed) is identical
#      for any (subject, operation, resource) triple regardless of `parameters`
#      content, when the handler does not depend on parameters.
#   2. No-execute-on-deny: the handler is never invoked unless the decision is
#      ALLOWED.
#   3. Allow-iff-triple-match: a request is ALLOWED iff (a) the subject is
#      active, (b) at least one policy rule matches with no matching DENY rule,
#      (c) at least one capability grant matches, and (d) a handler is
#      registered for the operation.
#   4. Audit-completeness: every decision is recorded in the audit log in the
#      exact order decisions were produced, and the resulting chain is replay
#      valid.
#
# The hand-crafted fuzz in scripts/fuzz_kernel_authorization.py stays as the
# small canary; this script is the deeper property surface.


SUBJECTS = (
    Subject("operator", "Operator", roles=("operator",)),
    Subject("auditor", "Auditor", roles=("auditor",)),
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


class _CallCounter:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def make(self, op: str) -> None:
        def _handler(resource: str, parameters):
            self.calls.append((op, resource))
            if op == "explode":
                raise RuntimeError("explode")
            return {"ok": True, "echoed": resource, "params": dict(parameters)}

        return _handler


def _request_allow_oracle(
    request: ActionRequest, handlers: dict[str, object]
) -> bool:
    """Reference oracle: would this triple be allowed under the registries?

    Mirrors the kernel's authorization algebra without touching the kernel.
    """
    if not request.request_id or not request.subject_id or not request.operation or not request.resource:
        return False
    if request.subject_id not in {s.subject_id for s in SUBJECTS if s.active}:
        return False
    # Policy oracle: deny if any matching rule is DENY; otherwise allow if any
    # matching rule is ALLOW. Mirrors PolicyEngine.evaluate ordering.
    matching = [rule for rule in POLICIES if rule.matches(request)]
    if any(rule.effect is PolicyEffect.DENY for rule in matching):
        return False
    if not any(rule.effect is PolicyEffect.ALLOW for rule in matching):
        return False
    # Capability oracle: any grant matches iff grant.subject_id == subject and
    # grant.operation and grant.resource are "*" or match.
    if not any(grant.matches(request) for grant in GRANTS):
        return False
    # Handler must be registered.
    if request.operation not in handlers:
        return False
    return True


def _generate_request(rng: random.Random, index: int) -> ActionRequest:
    return ActionRequest(
        request_id=f"pf-{index}",
        subject_id=rng.choice([s.subject_id for s in SUBJECTS]),
        operation=rng.choice(OPERATIONS),
        resource=rng.choice(RESOURCES),
        parameters={"seed": index, "noise": rng.randbytes(4).hex()},
    )


def _vary_parameters(request: ActionRequest, seed: int) -> ActionRequest:
    return ActionRequest(
        request_id=request.request_id,
        subject_id=request.subject_id,
        operation=request.operation,
        resource=request.resource,
        parameters={"variant": seed, "blob": [seed, seed + 1, "x" * (seed % 8)]},
    )


def _layer_decision_is_parameter_independent(
    request: ActionRequest, kernel: ConstitutionalKernel, seed: int
) -> bool:
    """Authorization layers (identity, policy, capability) ignore `parameters`.

    The kernel's authorization algebra depends only on (subject, operation,
    resource). Mutating parameters must not change identity resolution, policy
    decision, or capability decision. The handler may use parameters; that's
    fine — it's outside authorization.
    """
    twin = _vary_parameters(request, seed)
    if kernel.identities.resolve(request.subject_id) != kernel.identities.resolve(
        twin.subject_id
    ):
        return False
    if kernel.policies.evaluate(request) != kernel.policies.evaluate(twin):
        return False
    if kernel.capabilities.check(request) != kernel.capabilities.check(twin):
        return False
    return True


def main() -> int:
    iterations = 2000
    rng = random.Random(20260703)

    counter = _CallCounter()
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

    allowed = denied = failed = 0
    audit_event_ids: list[str] = []
    calls_before = 0  # baseline for invariant 2; refreshed after each iteration.

    for index in range(iterations):
        request = _generate_request(rng, index)
        oracle = _request_allow_oracle(request, handlers)

        # Invariant 1: parameter-independence. The three authorization layers
        # (identity, policy, capability) must produce identical decisions for
        # any parameters payload. We check the layers directly, not the
        # kernel, so the audit log gets exactly one event per iteration.
        if not _layer_decision_is_parameter_independent(request, kernel, index):
            print(f"FAIL: authorization layer is parameter-dependent on iteration {index}: {request}")
            return 1

        decision = kernel.handle(request)

        if decision.status is DecisionStatus.ALLOWED:
            allowed += 1
        elif decision.status is DecisionStatus.DENIED:
            denied += 1
        else:
            failed += 1

        # Invariant 2: no-execute-on-deny. Count handler calls before and
        # after; if the decision was not ALLOWED, the count must not have
        # changed. The counter baseline was taken above the kernel call.
        if decision.status is not DecisionStatus.ALLOWED and len(counter.calls) != calls_before:
            print(
                f"FAIL: denied/failed request executed handler on iteration {index}: {request} "
                f"reason={decision.reason!r}"
            )
            return 1
        if decision.status is DecisionStatus.ALLOWED and request.operation in handlers:
            new_calls = counter.calls[calls_before:]
            expected = (request.operation, request.resource)
            if expected not in new_calls:
                print(
                    f"FAIL: allowed request did not invoke expected handler on iteration {index}: {request} "
                    f"new_calls={new_calls} reason={decision.reason!r}"
                )
                return 1
        # Refresh baseline for the next iteration. We cannot use `calls_before`
        # for the *next* loop body because the kernel has now run; this
        # becomes the new pre-call count for the next iteration.
        calls_before = len(counter.calls)

        # Invariant 3: allow-iff-triple-match.
        if decision.allowed != oracle:
            print(
                f"FAIL: decision.allowed={decision.allowed} oracle={oracle} on iteration {index}: {request} "
                f"reason={decision.reason!r}"
            )
            return 1

        # Invariant 4 (per-iteration): every decision produces one audit
        # event, in order.
        if not decision.audit_event_id:
            print(f"FAIL: decision missing audit_event_id on iteration {index}: {request}")
            return 1
        audit_event_ids.append(decision.audit_event_id)
        if [event.event_id for event in kernel.audit_log.events] != audit_event_ids:
            print(f"FAIL: audit log order diverged on iteration {index}: {request}")
            return 1

    # Invariant 4 (end-of-run): full chain is replay valid.
    replay = ReplayVerifier().verify(kernel.audit_log.events)
    if not replay.valid:
        print(f"FAIL: replay invalid after property fuzz: {replay.reason}")
        return 1

    print(
        f"PASS: property fuzz authorization passed; iterations={iterations} "
        f"allowed={allowed} denied={denied} failed={failed} "
        f"audit_events={len(kernel.audit_log.events)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
