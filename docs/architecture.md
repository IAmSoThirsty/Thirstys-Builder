# Constitutional Builder Architecture

The Stage 1 architecture is a single-node governed execution kernel. External
reasoning systems submit `ActionRequest` objects. The kernel refuses to execute
until identity, policy, and capability checks all pass.

## Request Path

1. Request schema validation.
2. Subject resolution through `IdentityRegistry`.
3. Fail-closed policy evaluation through `PolicyEngine`.
4. Explicit capability check through `CapabilityRegistry`.
5. Deterministic plan construction through `Planner`.
6. Handler execution through a registered operation handler.
7. Hash-linked audit append.
8. Replay verification by `ReplayVerifier`.

## Trust Boundary

The reasoning layer is outside the trust boundary. It may propose actions, but
it cannot authorize itself. Authorization is performed only by the Builder
kernel.

## Data Boundary

Plans and audit records must not contain secrets. Production deployments must
use external secret stores and pass only opaque references through requests.

## Observability

Stage 1 exposes audit events and benchmark output. Production variants must add
metrics exporters, traces, health checks, alerts, and operator dashboards.

## Cluster Reference

The local cluster reference runs multiple independent `BuilderNode` kernels and
requires a quorum of allowed node decisions before returning a cluster allow.
Each node keeps its own audit chain. `FederationVerifier` verifies every node
chain and produces a deterministic federation hash over the merged evidence.
