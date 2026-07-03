# Security Threat Model

## Authorization and Policy Bypass

Threat: a caller attempts to execute a handler without policy approval.
Control: `ConstitutionalKernel.handle` calls policy evaluation before capability
checks, planning, or execution. No handler is resolved before these gates pass.

## Confused Deputy

Threat: a subject uses a broad tool to affect an unauthorized resource.
Control: capability grants bind subject, operation, and resource. Missing grants
deny by default.

## Audit Tampering

Threat: an attacker modifies audit history after execution.
Control: audit events include `previous_hash` and `event_hash`; replay verifies
the chain.

## Handler Failure

Threat: handler exceptions hide partial execution or produce false success.
Control: handler exceptions return a failed decision and append an audit event.

## Secret Leakage

Threat: plans or audit metadata include credentials.
Control: Stage 1 forbids secrets in plans and audit payloads. Production
variants must enforce secret scanning and external secret references.

## Supply Chain

Threat: dependencies alter governance behavior.
Control: Stage 1 uses only Python standard library runtime dependencies.
Local release evidence now includes SBOM, provenance, and deterministic
integrity signature files under `release/`, plus a deterministic ZIP package
and package manifest. The release package is signed with Ed25519; current local
artifacts use a deterministic test key while production signing can use
`CONSTITUTIONAL_BUILDER_ED25519_PRIVATE_KEY_PEM`. External production releases
must use managed key custody and published artifact attestations.
