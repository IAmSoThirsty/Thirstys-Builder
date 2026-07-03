# Volume 0 - Vision and Engineering Constitution

## Mission

Deliver a governed execution substrate that makes constitutional AI governance
objective, inspectable, replayable, and enforceable inside AI systems.

## Non-Negotiable Principles

- Governance is a first-class architectural primitive.
- Consequential action requires explicit authorization.
- Deterministic execution is preferred wherever feasible.
- No trust assumption is accepted without evidence.
- Reasoning layers are separated from execution and governance layers.
- Every material decision is observable, auditable, and replayable.

## Inputs

- Constitutional principles.
- Accountable deployment requirements.
- Operator identities and capabilities.
- Policy definitions.
- Action requests from an external reasoning or application layer.

## Outputs

- Governed execution decisions.
- Audit events.
- Replay transcripts.
- Metrics and health reports.
- Certification evidence.

## Preconditions

- A subject identity exists.
- The requested operation is declared.
- Policies and capabilities are loaded and versioned.

## Postconditions

- The request is allowed and executed, or denied with a reason.
- The decision is recorded in the audit chain.
- Replay can reconstruct the decision path.

## Failure Modes

- Missing identity: deny.
- Missing capability: deny.
- Missing policy coverage: deny.
- Audit write failure: deny.
- Non-deterministic handler output: flag and deny in high-assurance mode.

## Latency Budget

Single-node reference target: p95 decision latency below 25 ms for in-memory
identity, policy, capability, execution, audit, and replay metadata.

## Resource Requirements

The Stage 1 kernel runs in one process with standard-library Python and a local
JSONL audit log. Production variants must define CPU, memory, storage, and
network budgets per deployment class.

## Invariants

- No execution before identity, policy, and capability approval.
- No successful decision without an audit record.
- No audit record without a hash-chain predecessor reference.

## Traceability

- Requirements: CBEP-001, CBEP-002, CBEP-003, CBEP-004.
- Implementation: `source/constitutional_builder/`.
- Validation: `tests/`, `scripts/validate_repository.py`.

## Commander Audit

Signed-off for Stage 1 scope. Production cloud, cluster, edge, and
high-assurance expansions remain tracked in later volumes.
