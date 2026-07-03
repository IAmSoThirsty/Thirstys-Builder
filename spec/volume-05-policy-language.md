# Volume V - Policy Language Specification

## Policy Model

Stage 1 policies are declarative records with:

- policy id
- subject id or wildcard
- operation
- resource
- effect: allow or deny
- reason

## Inputs and Outputs

Inputs are action requests and policy records. Output is a deterministic
allow/deny decision with a reason and matched policy id.

## Preconditions and Postconditions

Policies must be versioned and schema-valid. Evaluation must return exactly one
effective decision. Explicit deny takes precedence over allow.

## Failure Modes

No matching policy, conflicting rules, invalid policy, or unavailable policy
store fail closed.

## Latency and Resources

Policy evaluation must be bounded by the loaded policy set. Stage 1 uses an
in-memory rule list.

## Invariants

- Default decision is deny.
- Explicit deny wins.
- Policy decisions are auditable.

## Traceability

Requirements: CBEP-001, CBEP-002.

## Commander Audit

Complete for local end-to-end policy semantics. Versioned policy bundles are
validated by `source/constitutional_builder/policy_bundle.py`; richer grammar,
schema evolution, and policy migration automation remain production expansion
work.
