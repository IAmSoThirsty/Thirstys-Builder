# Constitutional Builder Reference Repository

This repository is the initial execution-ready build for the Constitutional
Builder Engineering Program (CBEP). It contains the specification volumes,
traceability records, Commander audit artifacts, and a deterministic
single-node reference kernel vertical slice:

Identity -> Policy -> Capability -> Planner -> Execution -> Audit -> Replay

The current implementation is intentionally small, fail-closed, and dependency
light. It proves the governed execution path and gives independent engineering
teams a concrete baseline to extend into clustered, cloud, edge, and
high-assurance variants.

## Repository Map

- `spec/` - CBEP volumes, requirements, and traceability.
- `source/constitutional_builder/` - single-node reference kernel.
- `tests/` - deterministic unit tests for the vertical slice and gates.
- `benchmarks/` - local benchmark harness for kernel execution.
- `scripts/` - repository validation utilities.
- `formal/` - proof obligations and model-checking roadmap.
- `security/` - threat model and security controls.
- `docs/` - architecture, operations, and developer notes.
- `commander/` - Commander audit log and certification reports.

## Quick Validation

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

Run the local API:

```powershell
$env:PYTHONPATH='source'
python -m constitutional_builder.api --config deploy/example-config.json --port 8080
```

## Current Certification Status

Commander certification is recorded in
`commander/final-certification-report.md`. The current repository is certified
as a complete local reference foundation with self-hosted production deployment
gates: full local verification, Docker/Kubernetes smoke for the CBEP reference,
ThirstyAi Builder compose config, backend/frontend image builds, fail-closed
auth/Mongo startup checks, SBOM/provenance, package manifest, and release
signature. Multi-host consensus, cloud/edge/air-gapped production deployments,
external CI execution, independent security review, and production key custody
remain separately tracked production-expansion work.

## ThirstyAi Builder (the product)

The deployable product surface lives in `thirsty-ai-builder/`. It is the
11-page React + FastAPI + Mongo + Ollama product that the CBEP gates and
audits. To run it, read:

- `thirsty-ai-builder/README.md` — the 30-second pitch, lists, features,
  and FAQ.
- `thirsty-ai-builder/docs/DIAGRAMS.md` — system, request, pipeline,
  deploy, and trust-boundary diagrams.
- `thirsty-ai-builder/docs/INSTALL.md` — the full install matrix
  (Windows / macOS / Linux × local dev / Docker / production).
- `thirsty-ai-builder/DEPLOY.md` — the four production deploy paths.
