# ThirstyAi Builder

**A private, on-premises AI workspace that runs entirely on your machine.**
No API keys. No cloud account. No monthly bill. One command, one model,
one signed PDF per audit.

ThirstyAi Builder is a 11-page React app backed by a single-file FastAPI
service, MongoDB for persistence, a Rust CI auditor, and a **local
language model served by Ollama** on your own hardware. It is built and
signed by **Thirsty's Projects LLC** (Entity #14694374-0160). Every page
footer, every API response, and every signed audit PDF carries that
attribution.

If you want the deep dives — deploy paths, security policy, threat model,
hosted-Ollama runbook, installation matrix — they live next to this file:
`DEPLOY.md`, `SECURITY.md`, `THREAT_MODEL.md`, `HOSTED_OLLAMA.md`,
`docs/INSTALL.md`, `docs/DIAGRAMS.md`. This README is the front door.

---

## What it does (in plain English)

- **Talks to you** like a quiet assistant — Little Dove and Holli, both
  running on the local model.
- **Helps you run a business** — clients, invoices, deliverables, social
  posts, marketing copy, all in one app.
- **Answers questions from your own documents** (RAG). You point it at a
  file, it reads it, and when you ask a question it answers from your
  file, not the open internet.
- **Audits your code or any project** and produces a **signed PDF report**
  with your name, your LLC, and a tamper-evident Ed25519 signature.
- **Hosts an App Store** of small tools that you can extend or remove.

If the local model isn't running, the chat pages say so in plain English
and the rest of the app keeps working. No silent stubs, no fake answers.

---

## What's in it

### The 11 pages

| # | Page | What it does |
|---|------|--------------|
| 1 | **Home** | Landing + live system status (LLM provider, version, Mongo health) |
| 2 | **Commander** | Run audits, list past audits, download signed PDFs |
| 3 | **Little Dove** | Quiet conversational assistant on the local model |
| 4 | **Holli** | Operations assistant, audit-logged |
| 5 | **Architecture** | System topology, live |
| 6 | **App Store** | Installable tools, one row per tool |
| 7 | **Business Manager** | Clients, invoices, deliverables (CRUD) |
| 8 | **Socials** | Multi-channel post queue (Twitter, LinkedIn, Mastodon, Bluesky) |
| 9 | **Marketing** | Copy generator with brand-voice presets |
| 10 | **RAG** | Embed + query with deterministic cosine retrieval |
| 11 | **About** | Ownership block + IP inventory |

### The 7 App Store tools

| Tool | What it is |
|---|---|
| **Commander Audit** | Runs the verify_all gate and produces a signed PDF report |
| **Little Dove** | Quiet conversational assistant on the local Ollama model |
| **Holli** | Operations assistant, audit-logged, fails loud if Ollama is down |
| **RAG Embedder** | Retrieval-augmented generation; in-process vector store on Mongo |
| **Marketing Copy Generator** | LLM-backed copy with brand-voice presets |
| **Social Poster** | Cross-post to connected channels; secrets via env, never in Mongo |
| **Business Manager** | Clients, invoices, deliverables — Mongo-backed CRUD |

### The system

```
┌──────────────┐  HTTPS  ┌──────────────┐  same-origin  ┌────────────────┐
│   Browser    │ ──────▶ │ Reverse proxy│ ────────────▶ │  Frontend SPA  │
│  (React UI)  │         │  (TLS term)  │               │   (11 pages)   │
└──────────────┘         └──────────────┘               └───────┬────────┘
                                                                │ /api/*
                                                                ▼
                                                   ┌────────────────────────┐
                                                   │   Backend (FastAPI)    │
                                                   │   one file: server.py  │
                                                   └───┬──────────────┬─────┘
                                                       │              │
                                              compose net│              │Tailscale/WireGuard/SSH
                                                       ▼              ▼
                                            ┌──────────────┐   ┌──────────────┐
                                            │   MongoDB    │   │   Ollama     │
                                            │  (in ctr)    │   │  (loopback)  │
                                            └──────────────┘   └──────────────┘
```

Full diagrams (request flow, RAG pipeline, audit pipeline, deploy paths,
trust boundaries) are in `docs/DIAGRAMS.md`.

---

## Features

**For everyone**

- Private by default — runs on your hardware, nothing leaves unless you put it there
- Honest failures — no API key? No model running? The app says so plainly
- Client-ready deliverables — every audit exports as a signed PDF with your letterhead
- Whitelabel-ready — swap one SVG and the palette, ship a client edition
- Single-tenant — designed for one operator per deployment

**For engineers**

- One-file backend (`backend/server.py`) — every route in one place
- One-file-per-page frontend (`frontend/src/pages/*.jsx`)
- Fail-closed auth — `CB_API_KEY` (32-byte random bearer) + `THIRSTY_AI_REQUIRE_AUTH=1`
- Fail-closed persistence — `THIRSTY_AI_REQUIRE_MONGO=1` refuses to boot without Mongo
- Deterministic RAG — 32-dim hash-based vectors, no external embedding service
- Rate-limited (60 req/min/key) and size-capped (1 MiB bodies)
- Ed25519 release signing via PyCA, private key never enters the repo
- Reproducible release artifact — CycloneDX SBOM, manifest, signature under `release/`
- Container-hardened — non-root, `no-new-privileges`, `read_only: true`, capabilities dropped
- GitHub Action drop-in — `rust-auditor/.github/workflows/commander-audit.yml`

---

## Install

**Before you start, all paths need one thing: Ollama running on the same
host, with one model pulled.** That takes about 5 minutes.

```bash
# Windows / macOS:  https://ollama.com/download
# Linux:
curl -fsSL https://ollama.com/install.sh | sh

# Pull the default model (~5 GB)
ollama pull qwen2.5-coder:7b
```

### Path A — Local dev (Python venv + npm, ~10 min)

```bash
git clone <this-repo> thirsty-ai-builder
cd thirsty-ai-builder

# Backend
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Set CB_API_KEY to a fresh 32-byte random string
python server.py                                    # serves on :8001

# Frontend (separate terminal)
cd ../frontend
npm install
cp .env.example .env
npm start                                           # serves on :3000
```

Open http://localhost:3000. The footer shows your entity number.

### Path B — Docker Compose (~5 min)

```bash
git clone <this-repo> thirsty-ai-builder
cd thirsty-ai-builder
cp backend/.env.example backend/.env
# Set CB_API_KEY
docker compose up --build
# Backend on :8001, Frontend on :3000, Mongo on :27017
```

`host.docker.internal` lets the backend container reach the Ollama server
on your host.

### Path C — Production deploy

See `DEPLOY.md` for the four paths: **Railway** (~$5/mo, ~4 min),
**Vercel + Render** (free tier), **Fly.io** (`fly launch && fly deploy`),
or a self-managed **VPS** (Ubuntu 22.04+ with Docker + Ollama on the
host). All four converge on the same backend image and the same env-var
contract. After every deploy, run the preflight before exposing:

```bash
docker compose exec backend python -m thirsty_ai_builder_backend.preflight
# expected: PASS: thirsty-ai-builder production preflight
```

The full install matrix — Windows, macOS, Linux, every track, first-run
checks, uninstall — is in `docs/INSTALL.md`.

---

## Configuration

Every knob the Builder reads from the environment. Set them in
`backend/.env` for local dev, or in your platform's secret store for
production.

| Variable | Default | Required for prod? | Purpose |
|---|---|---|---|
| `CB_API_KEY` | *(none)* | **Yes** | 32-byte URL-safe bearer token for protected endpoints |
| `THIRSTY_AI_REQUIRE_AUTH` | `0` | **Yes (set to `1`)** | Fail-closed at startup if `CB_API_KEY` is missing |
| `MONGO_URL` | in-memory stub | **Yes** | MongoDB connection string |
| `THIRSTY_AI_REQUIRE_MONGO` | `0` | **Yes (set to `1`)** | Fail-closed at startup if Mongo is unreachable |
| `OLLAMA_HOST` | `http://127.0.0.1:11434` | No | Where the backend looks for the local model |
| `OLLAMA_MODEL` | `qwen2.5-coder:7b` | No | Which model to use for chat / RAG / Marketing |
| `CORS_ORIGINS` | `http://localhost:3000` | Yes | Comma-separated allowed origins; never use `*` with credentials |
| `THIRSTY_AI_TRUST_PROXY` | `0` | Only behind a trusted proxy | Trust `X-Forwarded-For` from a known reverse proxy |
| `THIRSTY_AI_MAX_REQUEST_BYTES` | `1048576` (1 MiB) | No | Body size cap |
| `THIRSTY_AI_REQUIRE_OLLAMA` | `0` | No (opt-in) | Fail-closed at startup if Ollama is unreachable |

If Ollama is down, the chat endpoints return **HTTP 503** with an
actionable message. The rest of the product keeps working.

---

## Ownership

This product is registered to **Thirsty's Projects LLC**
(Entity #14694374-0160).

- Principal office: 1450 South West Temple Street, A402, Salt Lake City, UT 84115-5203
- Registered agent: Entity Protect Registered Agent Services LLC, 169 W 2710 S Circle, STE 202A-65, Saint George, UT 84790-7205
- Contact: karrick1995@gmail.com

All rights reserved. See `LICENSE` and `OWNERSHIP.md`. The `/api/ownership`
endpoint and the `/about` page return the canonical ownership block; the
UI footer renders the copyright line on every page; every signed PDF
embeds the entity number with a SHA-256 attestation.

---

## More docs

- `DEPLOY.md` — the four production deploy paths in full
- `SECURITY.md` — reporting channel, hardening checklist, disclosure policy
- `THREAT_MODEL.md` — trust boundaries, top ten threats, mitigations
- `HOSTED_OLLAMA.md` — operator runbook for hosting Ollama off-box
- `docs/INSTALL.md` — full install matrix (Windows / macOS / Linux × dev / Docker / production)
- `docs/DIAGRAMS.md` — system, request, pipeline, deploy, and trust-boundary diagrams
- `OWNER_HANDOFF.md` — single-sheet operator hand-off
- `OWNERSHIP.md` — registration + IP inventory
- `CHANGELOG.md` — release notes
