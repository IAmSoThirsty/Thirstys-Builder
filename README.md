<div align="center">

# Constitutional Builder

**A deterministic, fail-closed governed-execution reference kernel.**
Identity → Policy → Capability → Planner → Execution → Audit → Replay.
One vertical slice, one Commander audit, one signed release.

[![License: Proprietary](https://img.shields.io/badge/License-Proprietary-red.svg)](thirsty-ai-builder/LICENSE)
[![Status: v0.2.0](https://img.shields.io/badge/status-v0.2.0-green.svg)](CHANGELOG.md)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](pyproject.toml)
[![Kernel: fail-closed](https://img.shields.io/badge/kernel-fail--closed-brightgreen.svg)](source/constitutional_builder/policy.py)
[![Audit: Ed25519](https://img.shields.io/badge/audit-Ed25519-brightgreen.svg)](scripts/sign_release_package.py)
[![SBOM: CycloneDX](https://img.shields.io/badge/sbom-CycloneDX-blue.svg)](release/sbom.json)
[![Spec: 18 volumes](https://img.shields.io/badge/spec-18%20volumes-purple.svg)](spec/)
[![Cert: local foundation](https://img.shields.io/badge/cert-local%20foundation-green.svg)](commander/final-certification-report.md)
[![Release signed](https://img.shields.io/badge/release-Ed25519%20signed-brightgreen.svg)](release/signing-public-key.pem)
[![Tests: 184 passing](https://img.shields.io/badge/tests-184%20passing-brightgreen.svg)](#)
[![Security: founderoftp@thirstysprojects.com](https://img.shields.io/badge/security-founderoftp%40thirstysprojects.com-blue.svg)](SECURITY.md)

[What it is](#what-it-is) · [Why care](#why-care) · [Why it exists](#why-it-exists) · [Architecture](#architecture) · [Quickstart](#quickstart) · [Tech stack](#tech-stack) · [Repository layout](#repository-layout) · [Development](#development) · [Deploy](#deploy) · [Roadmap](#roadmap) · [Security](#security) · [Docs](#docs) · [License](#license)

</div>

| Attribute | Value | Source |
|---|---|---|
| **License** | Proprietary, source-available under written agreement | [`thirsty-ai-builder/LICENSE`](thirsty-ai-builder/LICENSE) |
| **Version** | v0.2.0 | [`pyproject.toml`](pyproject.toml) |
| **Python** | 3.11+ | [`pyproject.toml`](pyproject.toml) |
| **Kernel** | fail-closed (deny by default) | [`source/constitutional_builder/policy.py`](source/constitutional_builder/policy.py) |
| **Audit log** | Ed25519-signed, hash-linked | [`scripts/sign_release_package.py`](scripts/sign_release_package.py) |
| **SBOM** | CycloneDX | [`release/sbom.json`](release/sbom.json) |
| **Spec** | 18 volumes | [`spec/`](spec/) |
| **Certification** | Local reference foundation, self-hosted production gates | [`commander/final-certification-report.md`](commander/final-certification-report.md) |
| **Status** | Reference foundation (multi-host / cloud / edge / air-gapped tracked separately) | [`commander/final-certification-report.md`](commander/final-certification-report.md) |

---

## What it is

**Constitutional Builder (CB)** is a deterministic, fail-closed reference
kernel for governed code execution. The same source runs as a Python
package, a gRPC service, a Docker container, a Kubernetes deployment, and
a CLI. The eight-stage pipeline — **Identity → Policy → Capability →
Planner → Execution → Audit → Replay** — is implemented as eight small
modules, each individually testable, each with a documented failure mode.

This repository is the **CBEP** — the Constitutional Builder Engineering
Program — and it contains the full set of artifacts needed to extend the
reference into clustered, cloud, edge, and high-assurance variants:

- The 18 spec volumes under `spec/` (vision, kernel, IR, policy language,
  runtime, security, distributed federation, APIs/SDKs, verification,
  benchmarks, certification, repo structure, operations, developer
  platform, governance, research).
- The reference kernel under `source/constitutional_builder/`.
- The deterministic test suite under `tests/`.
- The validation, conformance, fuzz, chaos, and release-signing scripts
  under `scripts/`.
- The Commander audit log and the final certification report under
  `commander/`.
- The deployable product surface — **ThirstyAI Builder** — under
  `thirsty-ai-builder/`, which the kernel gates and audits.

The repository is the engineering baseline. Every shipped commit is
audited by the Commander and recorded in
[`commander/audit-log.md`](commander/audit-log.md).

---

## Why care

If you build software that **takes consequential actions on behalf of
someone**, four properties matter: who is allowed to ask, what they are
allowed to ask for, whether the same ask produces the same result every
time, and whether you can prove after the fact what actually happened.

Most stacks get the first two by convention and the last two by
auditing whatever the cloud vendor happened to log. Constitutional
Builder makes all four **executable**: identity and capability are
typed objects, the policy bundle is the kernel (not a config file), the
planner is deterministic, and the audit log is hash-chained and
Ed25519-signed.

That is the operating premise. If you ship a system where "did this actually happen, and was it authorized" needs to be a yes with a receipt — not a vibe —
this is the reference kernel you extend.

For the longer argument, see [Why it exists](#why-it-exists) below.

---

## Why it exists

Most execution runtimes are permissive: an unauthorized request fails
open, an audit log is append-only until it isn't, and "deterministic
replay" is a marketing phrase.

Constitutional Builder takes the opposite position:

- **Identity is explicit.** Every actor has a typed identity object. No
  ambient authority, no hidden root.
- **Policy is a bundle, not a string.** The policy module is the kernel.
  Anything that doesn't pass the policy bundle does not execute.
- **Capability is granted per request.** Capabilities are typed, scoped,
  and short-lived. They cannot be widened at runtime.
- **Planner is deterministic.** Given the same input and the same policy,
  the planner produces the same plan. Replay is bit-exact.
- **Execution is gated.** Every consequential call passes through an
  authorization gate that fails closed.
- **Audit is hash-linked.** The audit log is append-only, hash-chained,
  and signed. A tampered entry is detectable.
- **Replay is a first-class operation.** Any past execution can be
  re-driven end-to-end and the result compared against the recorded one.

The eight stages are not aspirational. They are the modules
`identity.py`, `policy.py`, `capability.py`, `planner.py`, `kernel.py`,
`audit.py`, `replay.py`, plus the `cluster.py` federation layer and the
`grpc_server.py` / `api.py` surfaces. Each has a test file. Each has a
documented failure mode. The Commander audit log records every shipped
change against the gates in `scripts/verify_all.py`.

---

## Architecture

```
                                  ┌──────────────────────────┐
                                  │         Caller           │
                                  │  CLI / gRPC / HTTP / SDK │
                                  └────────────┬─────────────┘
                                               │
                                               ▼
   ┌────────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────┐  ┌──────────┐
   │  Identity  │─▶│  Policy  │─▶│Capability│─▶│ Planner  │─▶│Execution │─▶│   Audit   │─▶│  Replay  │
   │  module    │  │  bundle  │  │  grant   │  │ (determ.)│  │  (gated) │  │(hash-link)│  │(bit-exact)│
   └────────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └───────────┘  └──────────┘
         │              │             │              │              │              │             │
         └──────────────┴─────────────┴──────────────┴──────────────┴──────────────┴─────────────┘
                                                       │
                                                       ▼
                                              ┌─────────────────┐
                                              │   Commander     │
                                              │   audit log     │
                                              │   (Ed25519)     │
                                              └─────────────────┘
```

The full request flow, the cluster federation topology, the deploy
shapes (Docker, Kubernetes, single-node), and the trust boundaries are
drawn out in [`docs/architecture.md`](docs/architecture.md) and
[`docs/operations/runbook.md`](docs/operations/runbook.md).

The product surface this kernel ships to is the **ThirstyAI Builder** at
[`thirsty-ai-builder/`](thirsty-ai-builder/) — the kernel gates its
release, audits its dependency graph, and signs its deploy artifact.

---

## Quickstart

**Prereqs:** Python 3.11+ on PATH, `git` on PATH.

```bash
git clone https://github.com/IAmSoThirsty/Thirstys-Builder.git
cd Thirstys-Builder

# One command, the full local gate (unit tests + validators +
# conformance + fuzz + chaos + release evidence + signature):
python scripts/verify_all.py
```

Expected tail:

```
PASS  tests/test_vertical_slice
PASS  tests/test_policy_fail_closed
PASS  tests/test_audit_chain_verification
PASS  scripts/validate_repository
PASS  scripts/validate_api_contracts
PASS  scripts/validate_formal_models
PASS  scripts/fuzz_kernel_authorization
PASS  scripts/run_conformance
PASS  scripts/run_grpc_conformance
PASS  scripts/run_cluster_conformance
PASS  scripts/run_chaos_checks
PASS  scripts/validate_deployment
PASS  scripts/generate_release_evidence --check
PASS  scripts/build_release_package --check
PASS  scripts/sign_release_package --check
SUMMARY: 15/15 gates green
```

The gate runs the exact same checks the Commander uses in
certification. A green run is the contract.

**Run the kernel locally:**

```bash
# CLI
PYTHONPATH=source python -m constitutional_builder.cli --help

# HTTP API on :8080
PYTHONPATH=source python -m constitutional_builder.api \
  --config deploy/example-config.json --port 8080

# gRPC server
PYTHONPATH=source python -m constitutional_builder.grpc_server \
  --config deploy/example-config.json --port 50051
```

---

## Tech stack

| Layer | Choice | Version | Why |
|---|---|---|---|
| Language | Python | 3.11+ | Type-checked kernel, `match` statements, `asyncio` |
| Kernel | Hand-rolled modules | — | `identity`, `policy`, `capability`, `planner`, `kernel`, `audit`, `replay`, `cluster` — one module per stage, individually testable |
| API | FastAPI (HTTP) + grpcio (gRPC) | latest | Same business logic, two surfaces |
| Serialization | protobuf | 6.33+ | Stable wire format, gRPC-native |
| Crypto | PyCA `cryptography` | 46+ | Ed25519 release signing, deterministic key derivation |
| Build | setuptools + `pyproject.toml` | 68+ | Standard, no poetry/pipenv lock-in |
| Container | Docker + Compose | 24+ | Same artifact in dev and prod |
| Orchestration | Kubernetes | 1.27+ | `deploy/kubernetes.yaml` shipped, smoke-tested |
| Audit log | Hash-linked, append-only | — | Detects tampering, replayable end-to-end |
| Release artifact | CycloneDX SBOM + Ed25519 signature | — | Reproducible, verifiable, machine-checked |

The full dependency manifest is in [`pyproject.toml`](pyproject.toml).
The SBOM is in [`release/sbom.json`](release/sbom.json). The signing
public key is in [`release/signing-public-key.pem`](release/signing-public-key.pem).

---

## Repository layout

```
.
├── source/constitutional_builder/    the kernel — one module per pipeline stage
│   ├── identity.py                    explicit, typed actor identity
│   ├── policy.py                      policy bundle — the kernel of the kernel
│   ├── capability.py                  scoped, short-lived capability grants
│   ├── planner.py                     deterministic plan synthesis
│   ├── kernel.py                      gated execution, fail-closed
│   ├── audit.py                       hash-linked append-only log
│   ├── replay.py                      bit-exact re-drive of past executions
│   ├── cluster.py                     federation layer (volume 8)
│   ├── api.py                         FastAPI HTTP surface
│   ├── grpc_server.py                 gRPC surface
│   ├── cli.py                         constitutional-builder entrypoint
│   ├── models.py                      Pydantic models for every wire shape
│   └── config.py                      config loader + validator
├── spec/                              18 spec volumes + requirements.json
│   ├── volume-00-vision.md
│   ├── volume-01-mathematical-foundations.md
│   ├── volume-02-builder-kernel.md
│   ├── volume-03-builder-instruction-set.md
│   ├── volume-04-builder-intermediate-representation.md
│   ├── volume-05-policy-language.md
│   ├── volume-06-runtime-architecture.md
│   ├── volume-07-security-architecture.md
│   ├── volume-08-distributed-builder-federation.md
│   ├── volume-09-apis-sdks-interfaces.md
│   ├── volume-10-verification-formal-methods.md
│   ├── volume-11-benchmarks-performance.md
│   ├── volume-12-certification-framework.md
│   ├── volume-13-repository-structure.md
│   ├── volume-14-operations-sre.md
│   ├── volume-15-developer-platform.md
│   ├── volume-16-governance-rfc-stewardship.md
│   └── volume-17-research-track.md
├── tests/                             deterministic test suite (one file per stage)
├── scripts/                           the gate — every check the Commander runs
│   ├── verify_all.py                  one command → 15 green gates
│   ├── validate_repository.py
│   ├── validate_api_contracts.py
│   ├── install_formal_tools.py
│   ├── validate_formal_models.py
│   ├── fuzz_kernel_authorization.py
│   ├── property_fuzz_kernel_authorization.py
│   ├── model_check_authorization.py
│   ├── run_conformance.py
│   ├── run_grpc_conformance.py
│   ├── run_cluster_conformance.py
│   ├── run_chaos_checks.py
│   ├── verify_audit_chain.py
│   ├── generate_release_evidence.py
│   ├── build_release_package.py
│   ├── sign_release_package.py
│   ├── validate_deployment.py
│   └── validate_thirsty_ai_builder_deployment.py
├── deploy/                            Docker, Kubernetes, example config, runtime
├── formal/                            proof obligations + model-checking roadmap
├── security/                          threat model + security controls
├── docs/                              architecture, operations, developer notes
├── commander/                         audit log + final certification report
├── benchmarks/                        local benchmark harness
├── examples/                          runnable end-to-end examples
├── proto/                             protobuf definitions (gRPC wire)
├── sdk/                               client SDKs (TypeScript, PowerShell, …)
├── release/                           SBOM, package manifest, Ed25519 signature
├── pyproject.toml                     build manifest + dependencies
├── AGENTS.md                          agent operating contract for this repo
├── README.md                          this file
├── SECURITY.md                        security policy + reporting channel
└── LICENSE                            proprietary
```

The product surface this repository builds and ships is at
[`thirsty-ai-builder/`](thirsty-ai-builder/) — a separate README in that
folder describes the 11-page UI, the App Store, the install matrix, and
the deploy paths.

---

## Development

### Run the full local gate

The gate is the contract. Run it before any commit.

```bash
python scripts/verify_all.py
```

It runs, in order:

1. `python -m unittest discover -s tests` — deterministic unit tests
2. `python scripts/validate_repository.py` — repo structure + manifest
3. `python scripts/validate_api_contracts.py` — wire-shape stability
4. `python scripts/install_formal_tools.py` + `validate_formal_models.py`
   — proof-obligation scaffolding
5. `python scripts/fuzz_kernel_authorization.py` +
   `property_fuzz_kernel_authorization.py` — auth fuzzing
6. `python scripts/model_check_authorization.py` — bounded model check
7. `python scripts/run_conformance.py` + `run_grpc_conformance.py` +
   `run_cluster_conformance.py` — surface conformance
8. `python scripts/run_chaos_checks.py` — fault injection
9. `python scripts/verify_audit_chain.py` — audit log integrity
10. `python scripts/generate_release_evidence.py --check`
11. `python scripts/build_release_package.py --check`
12. `python scripts/sign_release_package.py --check`
13. `python scripts/validate_deployment.py` — deploy-shape validation
14. `python scripts/validate_thirsty_ai_builder_deployment.py` — product compose
15. `python benchmarks/benchmark_kernel.py --iterations 1000` — perf smoke
16. `python benchmarks/benchmark_suite.py --iterations 1000` — benchmark suite

### Run a single test

```bash
PYTHONPATH=source python -m unittest tests.test_vertical_slice
PYTHONPATH=source python -m unittest tests.test_policy_fail_closed
PYTHONPATH=source python -m unittest tests.test_audit_chain_verification
```

### Coding conventions

- **Python 3.11+, strict type hints on every public function.**
- **Pydantic models for every wire shape.** No raw dicts across module
  boundaries.
- **One module per pipeline stage.** Don't merge `identity.py` and
  `policy.py`; the seams are the test surfaces.
- **Fail closed.** Every gate that *could* fail open must fail closed
  by default and require an explicit opt-in to behave otherwise.
- **Commits: [Conventional Commits](https://www.conventionalcommits.org/).**
  `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`. Every
  commit that ships is audited by the Commander against the gate.

### Adding a new gate

1. Add the script to `scripts/` with a `--check` mode that exits 0 on
   pass and non-zero on fail.
2. Add a `tests/test_<name>.py` with at least one negative case.
3. Add a line to `scripts/verify_all.py` in the right order.
4. Add an entry to `commander/audit-log.md` and to the final
   certification report.
5. Open a PR. The CI runs the gate; the Commander audits the diff.

### Working on the product surface

The ThirstyAI Builder under `thirsty-ai-builder/` is the deployable
product. Its own README, install matrix, deploy paths, security policy,
and threat model are in that folder. The kernel gates that product's
release; the product surfaces the kernel.

---

## Deploy

Three deploy shapes, all under `deploy/`:

| Shape | File | Use it for |
|---|---|---|
| **Single-node (CLI / API / gRPC)** | `deploy/example-config.json` | Local dev, CI, smoke tests |
| **Docker Compose** | `deploy/docker-compose.yml` | Self-hosted production, single host |
| **Kubernetes** | `deploy/kubernetes.yaml` | Clustered reference, federation smoke |

Validate the chosen shape before exposing:

```bash
python scripts/validate_deployment.py --config deploy/example-config.json
# expected: PASS: constitutional-builder deployment config
```

For the product surface (ThirstyAI Builder), see
[`thirsty-ai-builder/DEPLOY.md`](thirsty-ai-builder/DEPLOY.md) for the
four production paths (Railway, Vercel + Render, Fly, VPS).

---

## Roadmap

- [x] 0.1 — Single-node reference kernel vertical slice (all 8 modules)
- [x] 0.1 — Deterministic test suite + 15-gate `verify_all.py`
- [x] 0.1 — CycloneDX SBOM + reproducible release package
- [x] 0.1 — Ed25519 release signing (per-machine keypair)
- [x] 0.1 — Docker + Kubernetes smoke for the CBEP reference
- [x] 0.1 — ThirstyAI Builder compose config + image builds audited
- [x] 0.1 — Fail-closed auth + Mongo startup checks
- [x] 0.1 — Commander certification as **local reference foundation
      with self-hosted production deployment gates**
      ([`commander/final-certification-report.md`](commander/final-certification-report.md))
- [ ] 0.2 — Multi-host consensus (CBEP volume 8) — actual federation,
      not just the conformance check
- [ ] 0.3 — Cloud reference deployment (AWS / GCP / Azure)
- [ ] 0.3 — Edge reference deployment (single-binary, offline Ollama)
- [ ] 0.4 — Air-gapped production deployment with offline model bundle
- [ ] 0.4 — External CI execution (the audit runs on a separate runner
      pool, not the build runner)
- [ ] 0.5 — Independent security review (paid external firm)
- [ ] 0.5 — KMS / HSM-backed release signing (replaces the per-machine
      keypair)
- [ ] 1.0 — High-assurance variant (formal proof of the policy
      module, volume 10 complete)

---

## Security

- **Reporting:** `founderoftp@thirstysprojects.com` with subject prefix
  `[security]`. 72-hour acknowledgement, 90-day disclosure window. See
  [`SECURITY.md`](SECURITY.md).
- **Threat model:** assets, adversaries, trust boundaries, and the
  top threats with mitigations in
  [`security/threat-model.md`](security/threat-model.md).
- **Cryptography:** Ed25519 release signing via PyCA `cryptography`.
  Audit log is hash-chained; tampering is detectable. Private signing
  keys never enter the repo.
- **Kernel defaults:** fail-closed authorization, deterministic
  planner, append-only audit. Any change to these defaults is itself
  audited by the Commander.

---

## Docs

| Document | Read it when you want to … |
|---|---|
| [`docs/architecture.md`](docs/architecture.md) | see the full system architecture |
| [`docs/operations/runbook.md`](docs/operations/runbook.md) | operate a running kernel in production |
| [`spec/`](spec/) | read the 18 spec volumes (kernel, policy, runtime, security, …) |
| [`formal/proof-obligations.md`](formal/proof-obligations.md) | see the proof-obligation roadmap |
| [`security/threat-model.md`](security/threat-model.md) | understand the trust boundaries and top threats |
| [`commander/audit-log.md`](commander/audit-log.md) | read the per-commit Commander audit log |
| [`commander/final-certification-report.md`](commander/final-certification-report.md) | read the current certification status |
| [`AGENTS.md`](AGENTS.md) | see the agent operating contract for this repo |
| [`thirsty-ai-builder/README.md`](thirsty-ai-builder/README.md) | read about the deployable product surface |
| [`thirsty-ai-builder/DEPLOY.md`](thirsty-ai-builder/DEPLOY.md) | deploy the product to Railway / Render / Fly / VPS |
| [`thirsty-ai-builder/docs/DIAGRAMS.md`](thirsty-ai-builder/docs/DIAGRAMS.md) | see the product diagrams |
| [`thirsty-ai-builder/docs/INSTALL.md`](thirsty-ai-builder/docs/INSTALL.md) | install the product on any OS |
| [`thirsty-ai-builder/SECURITY.md`](thirsty-ai-builder/SECURITY.md) | read the product's security policy |

---

## Maintainers

- **Jeremy Karrick** — founderoftp@thirstysprojects.com
- **Thirsty's Projects LLC** — Entity #14694374-0160
  - Registered agent: Entity Protect Registered Agent Services LLC, 169 W 2710 S Circle, STE 202A-65, Saint George, UT 84790-7205

The product surface (ThirstyAI Builder) is registered to the same
entity; see [`thirsty-ai-builder/OWNERSHIP.md`](thirsty-ai-builder/OWNERSHIP.md)
for the full filing details and IP inventory.

---

## License

**Source-available, not open source.** The kernel, the spec, and the
reference build in this repository are made available to independent
engineering teams under written agreement with the owner. There is no
public open-source license at the repository root.

- **Kernel + spec (this repository):** source-available; rights granted
  only by written agreement with the owner. Contact
  `founderoftp@thirstysprojects.com` to discuss evaluation, extension,
  or redistribution.
- **Deployable product (`thirsty-ai-builder/`):** proprietary license,
  all rights reserved. See
  [`thirsty-ai-builder/LICENSE`](thirsty-ai-builder/LICENSE) for the
  full grant-of-license text, the ownership-attribution clause, and the
  no-warranty terms.

If you forked or copied this work, the ownership block in
`OWNERSHIP.md` and the entity attribution on every page footer and
every signed PDF travel with it. That is intentional.

---

<div align="center">

© 2026 Jeremy Karrick / Thirsty's Projects LLC · Entity #14694374-0160 · All rights reserved

</div>
