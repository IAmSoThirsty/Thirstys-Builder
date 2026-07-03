from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .audit import InMemoryAuditLog
from .capability import CapabilityRegistry
from .identity import IdentityRegistry
from .models import ActionRequest, Decision, DecisionStatus, ExecutionResult
from .planner import Planner
from .policy import PolicyEngine

Handler = Callable[[str, dict[str, Any]], dict[str, Any]]


class ConstitutionalKernel:
    def __init__(
        self,
        *,
        identities: IdentityRegistry,
        policies: PolicyEngine,
        capabilities: CapabilityRegistry,
        audit_log: InMemoryAuditLog,
        handlers: dict[str, Handler] | None = None,
        planner: Planner | None = None,
    ) -> None:
        self.identities = identities
        self.policies = policies
        self.capabilities = capabilities
        self.audit_log = audit_log
        self.handlers = handlers or {}
        self.planner = planner or Planner()

    def handle(self, request: ActionRequest) -> Decision:
        try:
            request.validate()
        except ValueError as exc:
            return self._deny_or_fail(request, DecisionStatus.DENIED, str(exc), {})

        subject = self.identities.resolve(request.subject_id)
        if subject is None:
            return self._deny_or_fail(request, DecisionStatus.DENIED, "identity not found or inactive", {})

        policy = self.policies.evaluate(request)
        if not policy.allowed:
            return self._deny_or_fail(
                request,
                DecisionStatus.DENIED,
                policy.reason,
                {"policy_id": policy.policy_id},
            )

        capability = self.capabilities.check(request)
        if not capability.allowed:
            return self._deny_or_fail(
                request,
                DecisionStatus.DENIED,
                capability.reason,
                {"policy_id": policy.policy_id, "grant_id": capability.grant_id},
            )

        plan = self.planner.plan(request)
        handler = self.handlers.get(request.operation)
        if handler is None:
            return self._deny_or_fail(
                request,
                DecisionStatus.DENIED,
                "no handler registered for operation",
                {"policy_id": policy.policy_id, "grant_id": capability.grant_id, "plan": _plan_metadata(plan)},
            )

        try:
            step = plan.steps[0]
            output = handler(step.resource, step.parameters)
            result = ExecutionResult(operation=step.operation, resource=step.resource, output=output)
        except Exception as exc:  # noqa: BLE001 - handler failure must be audited and returned.
            return self._deny_or_fail(
                request,
                DecisionStatus.FAILED,
                f"handler failed: {exc}",
                {"policy_id": policy.policy_id, "grant_id": capability.grant_id, "plan": _plan_metadata(plan)},
            )

        event = self.audit_log.append(
            request_id=request.request_id,
            subject_id=request.subject_id,
            operation=request.operation,
            resource=request.resource,
            status=DecisionStatus.ALLOWED.value,
            reason="execution allowed",
            metadata={
                "policy_id": policy.policy_id,
                "grant_id": capability.grant_id,
                "plan": _plan_metadata(plan),
                "result": result.output,
            },
        )
        return Decision(
            request_id=request.request_id,
            status=DecisionStatus.ALLOWED,
            reason="execution allowed",
            audit_event_id=event.event_id,
            result=result,
        )

    def _deny_or_fail(
        self,
        request: ActionRequest,
        status: DecisionStatus,
        reason: str,
        metadata: dict[str, Any],
    ) -> Decision:
        event = self.audit_log.append(
            request_id=request.request_id or "<invalid>",
            subject_id=request.subject_id or "<invalid>",
            operation=request.operation or "<invalid>",
            resource=request.resource or "<invalid>",
            status=status.value,
            reason=reason,
            metadata=metadata,
        )
        return Decision(
            request_id=request.request_id,
            status=status,
            reason=reason,
            audit_event_id=event.event_id,
            result=None,
        )


def _plan_metadata(plan: Any) -> dict[str, Any]:
    return {
        "request_id": plan.request_id,
        "steps": [
            {
                "operation": step.operation,
                "resource": step.resource,
                "parameters": step.parameters,
            }
            for step in plan.steps
        ],
    }
