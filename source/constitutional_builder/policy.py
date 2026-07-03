from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .models import ActionRequest


class PolicyEffect(str, Enum):
    ALLOW = "allow"
    DENY = "deny"


@dataclass(frozen=True)
class PolicyRule:
    policy_id: str
    effect: PolicyEffect
    operation: str
    resource: str = "*"
    subject_id: str = "*"
    reason: str = ""

    def matches(self, request: ActionRequest) -> bool:
        subject_matches = self.subject_id in {"*", request.subject_id}
        operation_matches = self.operation in {"*", request.operation}
        resource_matches = self.resource in {"*", request.resource}
        return subject_matches and operation_matches and resource_matches


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    policy_id: str | None
    reason: str


class PolicyEngine:
    def __init__(self, rules: list[PolicyRule] | None = None) -> None:
        self._rules = tuple(rules or [])

    def evaluate(self, request: ActionRequest) -> PolicyDecision:
        matches = [rule for rule in self._rules if rule.matches(request)]
        if not matches:
            return PolicyDecision(False, None, "no matching policy")

        denials = [rule for rule in matches if rule.effect is PolicyEffect.DENY]
        if denials:
            rule = denials[0]
            return PolicyDecision(False, rule.policy_id, rule.reason or "explicit policy denial")

        allows = [rule for rule in matches if rule.effect is PolicyEffect.ALLOW]
        if allows:
            rule = allows[0]
            return PolicyDecision(True, rule.policy_id, rule.reason or "policy allowed")

        return PolicyDecision(False, None, "no effective policy")
