# Volume IV - Builder Intermediate Representation (BIR)

## BIR Shape

The Stage 1 BIR is a deterministic `ExecutionPlan` containing ordered
`ExecutionStep` records.

## Inputs and Outputs

Inputs are action requests and authorization context. Outputs are execution
plans with operation, handler, resource, and parameter bindings.

## Preconditions and Postconditions

The planner may only receive requests that passed identity, policy, and
capability checks. The resulting plan must be serializable for audit and replay.

## Failure Modes

Unsupported operation, non-serializable parameters, missing handler, or
non-deterministic plan construction fail closed.

## Latency and Resources

Plans are constructed in bounded memory with stable step ordering.

## Invariants

- Plans are immutable once audited.
- Plans contain no secrets.
- Plans are replay-addressable by request id.

## Traceability

Requirements: CBEP-001, CBEP-003.

## Commander Audit

Complete for Stage 1. Richer BIR optimization and distributed scheduling are
tracked in Volumes VI and VIII.
