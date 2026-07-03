from __future__ import annotations

from dataclasses import dataclass

from .models import ActionRequest


@dataclass(frozen=True)
class CapabilityGrant:
    grant_id: str
    subject_id: str
    operation: str
    resource: str = "*"

    def matches(self, request: ActionRequest) -> bool:
        return (
            self.subject_id == request.subject_id
            and self.operation in {"*", request.operation}
            and self.resource in {"*", request.resource}
        )


@dataclass(frozen=True)
class CapabilityDecision:
    allowed: bool
    grant_id: str | None
    reason: str


class CapabilityRegistry:
    def __init__(self, grants: list[CapabilityGrant] | None = None) -> None:
        self._grants = tuple(grants or [])

    def check(self, request: ActionRequest) -> CapabilityDecision:
        for grant in self._grants:
            if grant.matches(request):
                return CapabilityDecision(True, grant.grant_id, "capability granted")
        return CapabilityDecision(False, None, "no matching capability grant")
