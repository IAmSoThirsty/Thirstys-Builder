# Volume I - Mathematical Foundations

## Formal Model

The Builder is modeled as a transition system:

`S x R x P x C -> S' x D x A`

Where:

- `S` is governed state.
- `R` is an action request.
- `P` is the active policy set.
- `C` is the capability set.
- `D` is an allow or deny decision.
- `A` is the append-only audit event.

## Inputs and Outputs

Inputs are identities, policies, capabilities, requests, and current state.
Outputs are decisions, execution results, audit events, and replay transcripts.

## Preconditions and Postconditions

Preconditions: all inputs are schema-valid and versioned.
Postconditions: every transition is accepted into the audit chain or rejected
with a denial reason.

## Failure Modes

Invalid state, invalid request schema, policy ambiguity, capability mismatch,
clock drift, and audit-chain mismatch all fail closed.

## Latency and Resources

Mathematical validation must be separable from runtime evaluation. Runtime
checks use bounded, deterministic operations.

## Invariants

- Authorization monotonicity: denied requests cannot become allowed without a
  policy or capability version change.
- Audit integrity: event `n` commits to event `n-1`.
- Replay determinism: equivalent input logs produce equivalent transcripts.

## Traceability

Requirements: CBEP-001, CBEP-002, CBEP-003.

## Commander Audit

Complete for Stage 1 formal baseline. Full TLA+/Alloy models are tracked as
future proof work in `formal/proof-obligations.md`.
