# Volume VII - Security Architecture

## Security Goals

- Zero-trust execution boundary.
- Explicit identity and capability checks.
- Fail-closed policy behavior.
- Tamper-evident audit logs.
- No secret material in plans or audit payloads.

## Inputs and Outputs

Inputs are identities, credentials or attestations, policies, capabilities, and
requests. Outputs are authorization decisions, audit records, and security
metrics.

## Preconditions and Postconditions

Credentials and keys must be managed outside the Stage 1 reference kernel.
Production integrations must use secret stores and key rotation.

## Failure Modes

Credential failure, confused deputy, policy bypass attempt, audit tampering,
supply-chain compromise, and replay forgery.

## Latency and Resources

Security checks must be bounded and observable. Cryptographic operations in
production variants must publish p95 and p99 budgets.

## Invariants

- No identity means no execution.
- No capability means no execution.
- Audit hashes must verify before replay is trusted.

## Traceability

Requirements: CBEP-001, CBEP-002, CBEP-003.

## Commander Audit

Security baseline is complete for Stage 1. PKI, attestation, and remote
verification are tracked as production expansion.
