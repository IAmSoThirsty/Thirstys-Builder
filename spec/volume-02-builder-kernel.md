# Volume II - Builder Kernel

## Scope

The reference kernel implements the vertical slice:

Identity -> Policy -> Capability -> Planner -> Execution -> Audit -> Replay

## Inputs

Action requests, subject records, policy rules, capability grants, handlers,
and current audit chain state.

## Outputs

Execution decisions, optional handler results, denial reasons, audit events,
and replay transcripts.

## Preconditions

- Subject identity is known and active.
- Policy engine has at least one explicit rule for the operation.
- Capability registry has an explicit grant for the subject and operation.
- Audit log is writable.

## Postconditions

- Allowed requests execute exactly once.
- Denied requests do not execute.
- Every decision is recorded.

## Failure Modes

- Identity not found or disabled.
- Policy denial or no matching policy.
- Capability denial or no matching grant.
- Planner cannot produce deterministic plan.
- Handler failure.
- Audit append failure.

## Latency Budget

Single-node p95 target: below 25 ms per request in memory; below 100 ms with
local file audit persistence.

## Resource Requirements

One process, bounded in-memory registries, append-only JSONL audit file, and no
network dependency.

## Invariants

- Execution is impossible before authorization.
- Audit append is part of the request lifecycle.
- Denials are first-class audit events.

## Traceability

Requirements: CBEP-001, CBEP-002, CBEP-003.

## Commander Audit

Stage 1 kernel is implemented in `source/constitutional_builder/kernel.py` and
validated by `tests/test_vertical_slice.py`.
