# Proof Obligations

## PO-001 Fail-Closed Policy

Claim: if no policy allows a request, the kernel denies the request and does not
execute a handler.

Evidence:

- `source/constitutional_builder/policy.py`
- `tests/test_policy_fail_closed.py`
- `scripts/model_check_authorization.py`
- `scripts/fuzz_kernel_authorization.py`
- `formal/policy_authorization.als`

Future formalization: external Alloy execution for policy assertions.

## PO-002 Explicit Authorization

Claim: a successful execution requires active identity, policy allow, capability
grant, registered handler, and audit append.

Evidence:

- `source/constitutional_builder/kernel.py`
- `tests/test_vertical_slice.py`
- `formal/kernel_authorization_model.json`
- `formal/authorization_invariant.tla`

Future formalization: external TLA+ execution for state-machine invariants.

## PO-003 Audit Chain Integrity

Claim: audit event tampering is detected by replay verification.

Evidence:

- `source/constitutional_builder/audit.py`
- `source/constitutional_builder/replay.py`
- `tests/test_audit_replay.py`
- `scripts/run_chaos_checks.py`

Future formalization: hash-chain model and append-only storage assumptions.

## Known Proof Gaps

- TLA+ and Alloy starter models exist. `scripts/install_formal_tools.py`
  installs pinned external JARs, and `scripts/validate_formal_models.py`
  performs static checks plus TLA+ SANY parsing and Alloy command inspection
  when the JARs are present.
- Deterministic fuzzing exists; broader property-based fuzzing remains future
  work.
- The local cluster reference has quorum tests, but no distributed consensus
  proof exists yet.
