from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DecisionStatus(str, Enum):
    ALLOWED = "allowed"
    DENIED = "denied"
    FAILED = "failed"


@dataclass(frozen=True)
class ActionRequest:
    request_id: str
    subject_id: str
    operation: str
    resource: str
    parameters: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        required = {
            "request_id": self.request_id,
            "subject_id": self.subject_id,
            "operation": self.operation,
            "resource": self.resource,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise ValueError(f"missing required request fields: {', '.join(missing)}")


@dataclass(frozen=True)
class ExecutionStep:
    operation: str
    resource: str
    parameters: dict[str, Any]


@dataclass(frozen=True)
class ExecutionPlan:
    request_id: str
    steps: tuple[ExecutionStep, ...]


@dataclass(frozen=True)
class ExecutionResult:
    operation: str
    resource: str
    output: dict[str, Any]


@dataclass(frozen=True)
class Decision:
    request_id: str
    status: DecisionStatus
    reason: str
    audit_event_id: str
    result: ExecutionResult | None = None

    @property
    def allowed(self) -> bool:
        return self.status is DecisionStatus.ALLOWED
