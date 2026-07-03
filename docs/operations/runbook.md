# Operations Runbook

## Health Check

Run:

```powershell
python -m unittest discover -s tests
python scripts/validate_repository.py
python scripts/validate_api_contracts.py
python scripts/install_formal_tools.py
python scripts/validate_formal_models.py
python scripts/fuzz_kernel_authorization.py
python scripts/run_conformance.py
python scripts/run_grpc_conformance.py
python scripts/run_cluster_conformance.py
python scripts/run_chaos_checks.py
python scripts/generate_release_evidence.py --check
python scripts/build_release_package.py --check
python scripts/sign_release_package.py --check
python scripts/validate_deployment.py
python benchmarks/benchmark_kernel.py --iterations 1000
```

Or run the full local gate:

```powershell
python scripts/verify_all.py
```

Deployment validation performs Docker image build, container CLI smoke,
container API health smoke, Kubernetes client dry-run, local Docker Desktop
Kubernetes image import when available, and a temporary namespace apply/wait
smoke with cleanup.

Expected result: all commands print `PASS` or complete with an exit code of 0.

## Audit Verification

Use `ReplayVerifier` against the active audit log. A mismatch means the log is
not trustworthy for certification until restored from a known-good backup or
classified in an incident report.

## Failure Response

- Identity denial: verify subject registration and active state.
- Policy denial: inspect matching policy rules and explicit deny precedence.
- Capability denial: inspect grants for subject, operation, and resource.
- Handler failure: isolate handler exception and confirm the failed decision was
  audited.
- Audit failure: stop execution and repair storage before continuing.

## Backup and Recovery

For the Stage 1 `FileAuditLog`, back up JSONL files in append order. Restore
only to a clean path, then run replay verification before accepting the log.

## Upgrade Procedure

1. Run baseline validation.
2. Apply the change.
3. Update requirements, docs, tests, and Commander audit evidence.
4. Run validation again.
5. Record certification impact.
