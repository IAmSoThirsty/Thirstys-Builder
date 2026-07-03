# Volume VI - Runtime Architecture

## Lifecycle

1. Receive request.
2. Validate schema.
3. Resolve identity.
4. Evaluate policy.
5. Check capability.
6. Build plan.
7. Execute handler if allowed.
8. Append audit event.
9. Return decision.

## Inputs and Outputs

Inputs are requests, registries, handlers, and audit state. Outputs are
decisions, metrics, health reports, and replay records.

## Preconditions and Postconditions

Precondition: kernel components are initialized and health checks pass.
Postcondition: each request has one terminal decision.

## Failure Modes

Component unavailable, registry corruption, handler exception, audit failure,
replay mismatch, and resource exhaustion fail closed.

## Latency and Resources

Reference target: p95 below 25 ms in memory. Production variants must publish
SLOs per deployment class.

## Invariants

- Requests are terminal: allowed, denied, or failed.
- Handler failure is audited.
- Replay must not execute handlers.

## Traceability

Requirements: CBEP-002, CBEP-003.

## Commander Audit

Stage 1 lifecycle is implemented and tested. Distributed lifecycle is tracked in
Volume VIII.
