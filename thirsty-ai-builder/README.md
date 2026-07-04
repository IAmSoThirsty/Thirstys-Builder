<div align="center">

# ThirstyAI Builder

**A private, on-premises AI workspace. One command, one local model, one signed PDF per audit.**

[![License: Proprietary](https://img.shields.io/badge/License-Proprietary-red.svg)](LICENSE)
[![Status: v0.3.1](https://img.shields.io/badge/status-v0.3.1-green.svg)](CHANGELOG.md)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](backend/requirements.txt)
[![Node 18+](https://img.shields.io/badge/node-18+-blue.svg)](frontend/package.json)
[![LLM: Ollama local](https://img.shields.io/badge/llm-Ollama%20local-purple.svg)](https://ollama.com)
[![Database: MongoDB 6+](https://img.shields.io/badge/db-MongoDB%206%2B-green.svg)](docker-compose.yml)
[![Audit: Ed25519](https://img.shields.io/badge/audit-Ed25519-brightgreen.svg)](release/signing-public-key.pem)
[![SBOM: CycloneDX](https://img.shields.io/badge/sbom-CycloneDX-blue.svg)](release/sbom.json)
[![Code style: standard](https://img.shields.io/badge/code%20style-standard-black.svg)](backend/)
[![Tests: 184 passing](https://img.shields.io/badge/tests-184%20passing-brightgreen.svg)](#)
[![Security: founderoftp@thirstysprojects.com](https://img.shields.io/badge/security-founderoftp%40thirstysprojects.com-blue.svg)](SECURITY.md)

[What it is](#what-it-is) · [Why It Matters](#why-it-matters) · [Why it exists](#why-it-exists) · [Architecture](#architecture) · [Quickstart](#quickstart) · [Tech stack](#tech-stack) · [Development](#development) · [Deploy](#deploy) · [Roadmap](#roadmap) · [Docs](#docs) · [License](#license)

</div>

| Attribute | Value | Source |
|---|---|---|
| **License** | Proprietary, all rights reserved | [`LICENSE`](LICENSE) |
| **Status** | v0.3.1 | [`CHANGELOG.md`](CHANGELOG.md) |
| **Python** | 3.11+ | [`backend/requirements.txt`](backend/requirements.txt) |
| **Node** | 18+ | [`frontend/package.json`](frontend/package.json) |
| **LLM** | Ollama, local (no API key, no cloud) | [`HOSTED_OLLAMA.md`](HOSTED_OLLAMA.md) |
| **Database** | MongoDB 6.0+ | [`docker-compose.yml`](docker-compose.yml) |
| **Code style** | Standard (PEP 8 + Tailwind tokens) | [`backend/`](backend/) |
| **Release signing** | Ed25519 | [`release/signing-public-key.pem`](release/signing-public-key.pem) |
| **Security contact** | `founderoftp@thirstysprojects.com` | [`SECURITY.md`](SECURITY.md) |

---

## What it is

ThirstyAI Builder is a **self-hosted AI workspace** — 11-page React UI,
single-file FastAPI backend, MongoDB persistence, a Rust CI auditor, and
a **local language model served by Ollama** on your own hardware. No API
keys, no cloud account, no monthly bill.

It ships with seven tools out of the box: a quiet conversational
assistant, an operations assistant, a RAG pipeline over your own
documents, an audit engine that produces **tamper-evident signed PDFs**,
a marketing copy generator, a cross-channel social poster, and a
business manager (clients, invoices, deliverables).

If the local model isn't running, the chat pages say so in plain English
and the rest of the app keeps working. No silent stubs, no fake answers.

**Owner:** Jeremy Karrick / Thirsty's Projects LLC · Entity #14694374-0160

---

## Why It Matters

If you want a private AI workspace that **you** own — runs on your
hardware, signs its own audits, and is honest about what's on and what's
off — this is the build. No API keys to leak, no monthly bill, no
dependency on a third-party model API. If the local model isn't
running, the app says so. If the policy says no, the kernel says no.
The audit PDF you hand a client is signed and traceable to a named,
registered entity.

For most people, the practical question is just: "Can I run this on my
laptop today?" Yes — five minutes, one command, one model pull. See
[Quickstart](#quickstart) below.

For the longer argument about why an on-prem, owner-attested build
exists in the first place, see [Why it exists](#why-it-exists).

---

## Why it exists

Most "AI builder" products route every prompt through a third-party
cloud. The owner-attested model — where the artifact, the audit log, the
client deliverables, and the AI output are all signed and traceable to a
named, registered entity — is harder to build than the cloud version
because you have to do fail-closed auth, fail-closed persistence, and
release signing yourself.

This is that harder version. It runs on your hardware, signs every
audit as a PDF with your letterhead and an Ed25519 signature, and fails
closed at startup if the configuration is incomplete. It is a single
tenant, designed for one operator per deployment.

---

## Architecture

```
                         ┌─────────────────────┐
                         │   Browser (React)   │
                         │  11 pages, 1 SPA    │
                         └──────────┬──────────┘
                                    │ HTTPS
                                    ▼
                         ┌─────────────────────┐
                         │  Reverse proxy      │
                         │  Caddy or nginx     │
                         │  TLS + HSTS         │
                         └──────────┬──────────┘
                                    │ /api/*
                                    ▼
                         ┌─────────────────────┐
                         │  Backend (FastAPI)  │
                         │  one file:          │
                         │  server.py          │
                         └─────┬──────────┬────┘
                               │          │
                  compose net  │          │  Tailscale / WireGuard / SSH
                               ▼          ▼
                    ┌──────────────┐  ┌──────────────┐
                    │   MongoDB    │  │   Ollama     │
                    │  loopback    │  │  loopback    │
                    │  no auth     │  │  no auth     │
                    └──────────────┘  └──────────────┘
```

The four trust boundaries, the request flow, the RAG and audit
pipelines, and the deploy paths are drawn out in detail in
[`docs/DIAGRAMS.md`](docs/DIAGRAMS.md).

---

## Quickstart

**Prereq:** [Ollama](https://ollama.com) running on the same host, with
one model pulled. ~5 minutes.

```bash
# Linux
curl -fsSL https://ollama.com/install.sh | sh && ollama pull qwen2.5-coder:7b
# macOS / Windows: install from ollama.com/download, then
#   ollama pull qwen2.5-coder:7b
```

**Run the stack with one command (~5 min):**

```bash
git clone https://github.com/IAmSoThirsty/Thirstys-Builder.git
cd Thirstys-Builder/thirsty-ai-builder
cp backend/.env.example backend/.env
# Set CB_API_KEY to a fresh 32-byte random string:
#   python -c "import secrets; print(secrets.token_urlsafe(32))"
docker compose up --build
# Backend on :8001 · Frontend on :3000 · Mongo on :27017
```

Open <http://localhost:3000>. The footer on every page shows your
entity number. Open **Little Dove** to chat with your local model.

> The full install matrix (Windows / macOS / Linux × dev / Docker /
> production), first-run checks, and uninstall are in
> [`docs/INSTALL.md`](docs/INSTALL.md).

---

## Tech stack

| Layer | Choice | Version | Why |
|---|---|---|---|
| Frontend | React | 18.2 | Single SPA, one file per page |
| UI primitives | Tailwind CSS | 3.4 | Tokens-driven, no custom design system drift |
| Motion | Framer Motion | 11.0 | Page transitions, no jank |
| Backend | FastAPI | 0.110+ | One file, every route, async, type-checked |
| ASGI server | Uvicorn | 0.27+ | Standard, fast, hot-reload |
| Validation | Pydantic | 2.5+ | Request/response models, `max_length` everywhere |
| Database | MongoDB | 6.0+ | Document-shaped CRUD, vector storage for RAG |
| LLM | Ollama | latest | Local, no auth, GGUF models on your hardware |
| Default model | qwen2.5-coder:7b | 7B / 5 GB | Default chat + code model; swappable |
| CI auditor | Rust | 1.75+ | Single binary, gates CI against the Commander |
| Release signing | Ed25519 (PyCA) | — | Per-machine keypair, public key in `release/` |
| Container runtime | Docker + Compose | 24+ | Same artifact in dev and prod |

The full dependency manifest is in [`backend/requirements.txt`](backend/requirements.txt)
and [`frontend/package.json`](frontend/package.json). The CycloneDX
SBOM is in [`release/sbom.json`](release/sbom.json).

---

## Development

### Repository layout

```
thirsty-ai-builder/
├── backend/                       FastAPI (Python) — every API endpoint
│   └── thirsty_ai_builder_backend/
│       ├── server.py              the main app, every route, one file
│       ├── app_store.py           SEED_TOOLS — add a row, ship a tool
│       ├── ownership.py           canonical entity block
│       ├── letterhead.py          audit PDF letterhead + SHA-256
│       └── preflight.py           production preflight (run before expose)
├── frontend/                      React + Tailwind + Framer Motion
│   └── src/
│       ├── App.jsx                router
│       ├── pages/                 one file per page (Home, Commander, …)
│       ├── components/            ThirstyLogo, AuthTokenControl, …
│       └── index.css              palette + tokens
├── rust-auditor/                  Rust CLI that gates CI
│   └── .github/workflows/
│       └── commander-audit.yml    drop-in GitHub Action
├── docs/
│   ├── DIAGRAMS.md                system, request, pipeline diagrams
│   └── INSTALL.md                 full install matrix
├── deploy/                        Caddyfile, nginx.conf, ollama.service
├── release/                       SBOM, package manifest, Ed25519 sig
├── docker-compose.yml             one command → whole stack
├── DEPLOY.md                      4 production deploy paths
├── SECURITY.md                    policy + hardening checklist
├── THREAT_MODEL.md                trust boundaries + top 10 threats
├── HOSTED_OLLAMA.md               Ollama-on-a-different-host runbook
├── OWNER_HANDOFF.md               single-sheet operator hand-off
├── OWNERSHIP.md                   registration + IP inventory
├── CHANGELOG.md                   release notes
├── LICENSE                        proprietary
└── design_guidelines.json         design system
```

### Local dev (hot reload)

Two terminals.

```bash
# Terminal 1 — backend on :8001
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python server.py

# Terminal 2 — frontend on :3000
cd frontend
npm install
cp .env.example .env
npm start
```

### Tests

The verify_all gate runs the full local test + validation suite. It is
the same script the Commander audit harness runs in CI.

```bash
cd ../thirsty-ai-builder     # this directory
python -m unittest discover -s ../thirsty-ai-builder/backend/tests
# or the full gate:
cd .. && python scripts/verify_all.py
```

### Production preflight (before exposing)

```bash
docker compose exec backend python -m thirsty_ai_builder_backend.preflight
# expected: PASS: thirsty-ai-builder production preflight
```

The preflight refuses to pass if `CB_API_KEY` is missing, short, or
placeholder-looking, if Mongo is unreachable, or if required env vars
are absent.

### Coding conventions

- Backend: PEP 8, type hints on every public function, Pydantic models
  for every request/response, `max_length` on every free-text field.
- Frontend: one component per file, Tailwind tokens (no inline hex),
  no `useEffect` for derived state.
- Commits: [Conventional Commits](https://www.conventionalcommits.org/)
  (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`).
- Every PR that touches behavior must include a test. The verify_all
  gate is the contract; the audit workflow in
  `rust-auditor/.github/workflows/commander-audit.yml` runs it on every PR.

### Swapping the model

```bash
ollama pull mistral   # or llama3.2, codestral, phi3, …
# in backend/.env:
OLLAMA_MODEL=mistral
# restart the backend
```

The Builder uses that model for all chat endpoints (Little Dove, Holli,
Marketing, RAG answer). RAG embeddings stay deterministic in-process.

### Adding an App Store tool

Append a row to `SEED_TOOLS` in
`backend/thirsty_ai_builder_backend/app_store.py`. The UI picks the new
row up on the next request — no rebuild required.

---

## Deploy

Four paths, all documented in [`DEPLOY.md`](DEPLOY.md):

| Path | Cost | Time | Best for |
|---|---|---|---|
| **Railway** | ~$5/mo | ~4 min | Fastest public deploy |
| **Vercel + Render** | Free tier | ~10 min | Free hosting, Atlas free Mongo |
| **Fly.io** | $0–$5 | ~5 min | `fly launch && fly deploy` |
| **VPS** (Ubuntu 22.04+) | $5–$40/mo | ~30 min | Full control, Ollama on the host |

All four converge on the same backend image and the same env-var
contract. The hardening checklist in
[`SECURITY.md`](SECURITY.md) applies to all four.

---

## Roadmap

- [x] 1.0 — Self-hosted production deployment gates (commit `fecfdf6`)
- [x] 1.0 — Hosted Ollama runbook + TLS termination configs (commit `b610313`)
- [x] 1.0 — Auth middleware + Mongo selection + readiness probe (commit `0065de4`)
- [x] 1.0 — CycloneDX SBOM + reproducible release artifact (Ed25519)
- [ ] 1.1 — Multi-user (still single-tenant per deployment, but multiple
      operators per installation with per-op audit trails)
- [ ] 1.2 — Clustered reference deployment (CBEP volume 8)
- [ ] 2.0 — Air-gapped production deployment with offline Ollama bundle
- [ ] 2.0 — External CI execution (the Rust auditor runs on its own runner pool)
- [ ] 2.0 — KMS / HSM-backed release signing (replaces the per-machine keypair)

---

## Security

- **Reporting:** `founderoftp@thirstysprojects.com` with subject prefix `[security]`.
  72-hour acknowledgement, 90-day disclosure window. See
  [`SECURITY.md`](SECURITY.md).
- **Threat model:** assets, adversaries, four trust boundaries, and the
  top ten threats with mitigations in
  [`THREAT_MODEL.md`](THREAT_MODEL.md).
- **Cryptography:** Ed25519 release signing via PyCA. Opaque 32-byte
  random auth tokens (not JWTs) with `hmac.compare_digest`. TLS
  terminated at the reverse proxy. Private signing keys never enter the
  repo.
- **Hardening checklist** for self-hosted deployments:
  [`SECURITY.md`](SECURITY.md) §"Hardening checklist for self-hosted
  deployments".

---

## Docs

| Document | Read it when you want to … |
|---|---|
| [`docs/DIAGRAMS.md`](docs/DIAGRAMS.md) | see the system, request, pipeline, deploy, and trust-boundary diagrams |
| [`docs/INSTALL.md`](docs/INSTALL.md) | install on Windows / macOS / Linux, in dev / Docker / production |
| [`DEPLOY.md`](DEPLOY.md) | ship to Railway, Vercel+Render, Fly, or a VPS |
| [`SECURITY.md`](SECURITY.md) | report a vulnerability or harden a self-hosted deployment |
| [`THREAT_MODEL.md`](THREAT_MODEL.md) | understand the trust boundaries and the top ten threats |
| [`HOSTED_OLLAMA.md`](HOSTED_OLLAMA.md) | run Ollama on a separate host (Tailscale / WireGuard / SSH) |
| [`OWNER_HANDOFF.md`](OWNER_HANDOFF.md) | get the single-sheet operator hand-off |
| [`OWNERSHIP.md`](OWNERSHIP.md) | see the registration + IP inventory |
| [`CHANGELOG.md`](CHANGELOG.md) | see what changed in each release |
| [`design_guidelines.json`](design_guidelines.json) | see the design system (colors, type, spacing, voice) |
| [`release/`](release/) | see the SBOM, package manifest, and Ed25519 signature for the current release |

---

## Maintainers

- **Jeremy Karrick** — founderoftp@thirstysprojects.com
- **Thirsty's Projects LLC** — Entity #14694374-0160
  - Registered agent: Entity Protect Registered Agent Services LLC, 169 W 2710 S Circle, STE 202A-65, Saint George, UT 84790-7205

See [`OWNERSHIP.md`](OWNERSHIP.md) for the full filing details and the
IP inventory.

---

## License

**Proprietary, all rights reserved.** The deployable product in this
folder is licensed under the terms in [`LICENSE`](LICENSE). The kernel
and spec at the repository root are source-available under written
agreement with the owner (see the top-level `README.md` for the split
between kernel/spec and deployable product).

No third party may sublicense, resell, fork for redistribution, or
remove the attribution. Independent developers may be engaged under
written agreement with the owner. Contact
`founderoftp@thirstysprojects.com` to discuss evaluation, extension,
or redistribution.

---

<div align="center">

© 2026 Jeremy Karrick / Thirsty's Projects LLC · Entity #14694374-0160 · All rights reserved

</div>
