# Volume III - Builder Instruction Set (BIS)

## Instruction Classes

- `authorize`: bind identity, policy, and capability checks.
- `plan`: produce deterministic execution steps.
- `execute`: run an approved handler.
- `audit`: append hash-linked evidence.
- `replay`: reconstruct prior decisions.

## Inputs and Outputs

Inputs are typed request objects and registry state. Outputs are decisions,
plans, execution results, and audit records.

## Preconditions and Postconditions

Every instruction requires a request id and subject id. Every completed
instruction emits an audit-observable state transition.

## Failure Modes

Unknown instruction, invalid operands, missing authorization, handler failure,
and audit failure all deny or abort without hidden state changes.

## Latency and Resources

BIS instructions must remain bounded and deterministic for Stage 1.

## Invariants

- No BIS instruction may bypass the policy engine.
- Every state-changing instruction requires an audit event.

## Traceability

Requirements: CBEP-001, CBEP-002.

## Commander Audit

Complete for the Stage 1 instruction vocabulary used by the reference kernel.
