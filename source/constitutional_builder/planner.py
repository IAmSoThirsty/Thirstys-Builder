from __future__ import annotations

from .models import ActionRequest, ExecutionPlan, ExecutionStep


class Planner:
    def plan(self, request: ActionRequest) -> ExecutionPlan:
        step = ExecutionStep(
            operation=request.operation,
            resource=request.resource,
            parameters=dict(sorted(request.parameters.items())),
        )
        return ExecutionPlan(request_id=request.request_id, steps=(step,))
