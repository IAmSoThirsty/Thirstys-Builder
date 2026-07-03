# Volume VIII - Distributed Builder and Federation

## Scope

This volume defines the expansion path from the single-node kernel to clustered
and federated builders.

## Inputs and Outputs

Inputs include node identities, replicated policy bundles, capability grants,
federation contracts, and distributed audit streams. Outputs include consensus
decisions, merged audit evidence, and federation health reports.

## Preconditions and Postconditions

Nodes must be attested and policy-compatible before federation. Cross-node
actions must preserve authorization and replay semantics.

## Failure Modes

Network partition, split brain, clock skew, node compromise, log divergence,
schema mismatch, and federation contract breach.

## Latency and Resources

Distributed variants must define per-hop latency, quorum latency, and recovery
time objectives.

## Invariants

- Federation cannot weaken local authorization.
- Audit logs must remain merge-verifiable.
- Partition behavior must be explicit.

## Traceability

Requirements: CBEP-001, CBEP-003.

## Commander Audit

Local clustered reference implementation exists in
`source/constitutional_builder/cluster.py`. It provides deterministic quorum
decisions and federation audit verification. Live multi-host deployment,
consensus protocols, and partition recovery remain production expansion work.
