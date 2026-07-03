# ThirstyAi Builder

> **Owner-attested, governance-first, dep-light AI builder. Runs entirely on your machine.**

---

## The 30-Second Pitch

### If you're not an engineer

ThirstyAi Builder is a **private, on-premises AI workspace** that you run on
your own computer or your own server. It is not a cloud product. Nothing you
type, write, or store with it leaves your machine unless you choose to put it
on the public internet yourself.

It does five everyday jobs out of the box:

1. **Talks to you** like a quiet assistant (Little Dove).
2. **Helps you run your business** — clients, invoices, deliverables, social
   posts, marketing copy.
3. **Answers questions from your own documents** (RAG — Retrieval-Augmented
   Generation). You point it at a file, it reads it, and when you ask a
   question it answers from your file, not from the open internet.
4. **Audits your code or any project** and produces a **signed PDF report**
   with your name, your LLC, and a tamper-evident signature.
5. **Hosts an App Store of small tools** you can extend or remove.

The "AI" in it is a **local language model served by Ollama** — an open-source
program that runs models on your hardware. You do not need an OpenAI key, an
Anthropic key, or any cloud account. You do not pay a monthly bill. If the
model isn't running, the app says so plainly and the rest of the product
still works.

It is built and signed by **Thirsty's Projects LLC** (Entity #14694374-0160).
Every page, every PDF, and every API response carries that attribution.

### If you are an engineer

FastAPI backend (one file, `server.py`) + React 11-page SPA + MongoDB
persistence + a Rust CI auditor + a Commander that signs every audit as an
Ed25519 PDF. LLM is **Ollama on loopback** (`OLLAMA_HOST`, default
`http://127.0.0.1:11434`, default model `qwen2.5-coder:7b`). Fail-closed
auth (`CB_API_KEY` + `THIRSTY_AI_REQUIRE_AUTH=1`) and fail-closed Mongo
(`THIRSTY_AI_REQUIRE_MONGO=1`). Release artifact is a deterministic
CycloneDX SBOM, package manifest, and Ed25519 signature under `release/`.
No `node_modules/`, no compiled artifacts in the repo. Fresh install every
time. See `docs/DIAGRAMS.md` for the topology, `docs/INSTALL.md` for the
install matrix, `DEPLOY.md` for the four production paths, `SECURITY.md`
and `THREAT_MODEL.md` for the trust boundaries.

### If you have 60 seconds to look at a picture

Open `docs/DIAGRAMS.md` §1. It is one ASCII box-and-arrow picture of the
whole system. Everything else in this README is commentary on that picture.

---

## Table of Contents

1. [The 30-Second Pitch](#the-30-second-pitch)
2. [Repository Map](#repository-map)
3. [What Ships — The 11-Page UI](#what-ships--the-11-page-ui)
4. [What Ships — The 7 App Store Tools](#what-ships--the-7-app-store-tools)
5. [Features at a Glance](#features-at-a-glance)
6. [Diagrams](#diagrams)
7. [Installation Methods](#installation-methods)
8. [Configuration Reference](#configuration-reference)
9. [Daily Operations](#daily-operations)
10. [Deploy to Production](#deploy-to-production)
11. [Security & Threat Model](#security--threat-model)
12. [Ownership, License, and IP](#ownership-license-and-ip)
13. [Pointers to the Rest of the Docs](#pointers-to-the-rest-of-the-docs)
14. [FAQ](#faq)

---

## Repository Map

```
thirsty-ai-builder/
├── backend/                 ← FastAPI (Python) — every API endpoint lives here
│   └── thirsty_ai_builder_backend/
│       ├── server.py        ← the main app (one file, every route)
│       ├── app_store.py     ← SEED_TOOLS array — add a row, ship a new tool
│       ├── ownership.py     ← canonical ownership block (entity #, address)
│       ├── letterhead.py    ← audit PDF letterhead + SHA-256 attestation
│       └── preflight.py     ← production preflight (run before exposing)
├── frontend/                ← React + Tailwind + Framer Motion — the 11-page UI
│   └── src/
│       ├── App.jsx          ← router
│       ├── pages/           ← one file per page (Home, Commander, …)
│       ├── components/      ← ThirstyLogo, AuthTokenControl, …
│       └── index.css        ← palette + design tokens
├── rust-auditor/            ← Rust CLI that gates CI against the Commander
│   └── .github/workflows/commander-audit.yml   ← drop-in GitHub Action
├── docs/                    ← DIAGRAMS.md, INSTALL.md (this README points here)
├── docker-compose.yml       ← one command to run the whole stack
├── README.md                ← this file
├── DEPLOY.md                ← 4 deploy paths (Railway, Vercel+Render, Fly, VPS)
├── INSTALL.md               ← alias for docs/INSTALL.md
├── SECURITY.md              ← security policy + hardening checklist
├── THREAT_MODEL.md          ← trust boundaries + top 10 threats
├── HOSTED_OLLAMA.md         ← runbook for hosting Ollama off-box
├── LICENSE                  ← proprietary license (Thirsty's Projects LLC)
├── OWNERSHIP.md             ← registration + IP inventory
├── OWNER_HANDOFF.md         ← single-sheet operator hand-off
├── CHANGELOG.md             ← release notes
└── design_guidelines.json   ← the design system (tokens, voice, footer)
```

---

## What Ships — The 11-Page UI

The frontend is a single React application. Each page is one file under
`frontend/src/pages/`. The footer on every page renders the canonical
ownership line; the `/about` page renders the full ownership block.

| # | Page | What it does | Backed by |
|---|------|--------------|-----------|
| 1 | **Home** | Landing + live system status (LLM provider, version, Mongo health) | `/api/health` |
| 2 | **Commander** | Run audits, list past audits, download signed PDFs | `/api/audit/*` |
| 3 | **Little Dove** | Quiet conversational assistant | Local Ollama |
| 4 | **Holli** | Operations assistant (audit-logged) | Local Ollama |
| 5 | **Architecture** | System topology view (live) | `/api/architecture` |
| 6 | **App Store** | Installable tools, one row per tool | `SEED_TOOLS` |
| 7 | **Business Manager** | Clients, invoices, deliverables (CRUD) | MongoDB |
| 8 | **Socials** | Multi-channel post queue (Twitter, LinkedIn, Mastodon, Bluesky) | MongoDB + env credentials |
| 9 | **Marketing** | Copy generator with brand-voice presets | Local Ollama |
| 10 | **RAG** | Embed + query with deterministic cosine retrieval | Local Ollama for the answer |
| 11 | **About** | Ownership block + IP inventory | `/api/ownership` |

---

## What Ships — The 7 App Store Tools

The App Store page renders rows from a single array,
`SEED_TOOLS` in `backend/thirsty_ai_builder_backend/app_store.py`. To add a
tool, append a dict; the UI picks it up automatically.

| ID | Name | Category | Version | What it is |
|---|---|---|---|---|
| `commander-audit` | **Commander Audit** | governance | 0.1.0 | Runs the verify_all gate and produces a signed PDF |
| `little-dove` | **Little Dove** | assistant | 1.0.0 | Quiet conversational assistant on the local Ollama model |
| `holli` | **Holli** | assistant | 1.0.0 | Operations assistant; audit-logged; 503 if Ollama is down |
| `rag-embedder` | **RAG Embedder** | rag | 0.2.0 | Retrieval-augmented generation; in-process vector store backed by Mongo |
| `marketing-copy` | **Marketing Copy Generator** | marketing | 1.0.0 | LLM-backed copy with brand-voice presets |
| `social-poster` | **Social Poster** | social | 0.1.0 | Cross-post to connected channels; secrets via env, not Mongo |
| `business-manager` | **Business Manager** | operations | 1.0.0 | Clients, invoices, deliverables — Mongo-backed CRUD with audit log per write |

---

## Features at a Glance

### For non-engineers

- **Private by default.** Runs on your hardware. No API keys. No cloud account.
- **Honest failures.** If Ollama is down, the chat pages say so in plain
  English and a 503 with a clear message. No silent stubs in production.
- **Client-ready deliverables.** Audits export as **signed PDFs** with your
  letterhead, your entity number, and a SHA-256 body hash.
- **Whitelabel-ready.** Swap one SVG (`ThirstyLogo.jsx`) and the palette
  in `tailwind.config.js` to ship a client-specific edition.
- **Single-tenant.** Designed for one operator per deployment, not thousands
  of strangers sharing a server.
- **Owner-attested.** Every page footer, every API response, every signed
  PDF carries the Thirsty's Projects LLC attribution and entity number.

### For engineers

- **One-file backend.** Every route lives in `backend/server.py`. No hidden
  framework magic. Onboard a new dev in a day.
- **One-file-per-page frontend.** `frontend/src/pages/*.jsx` — one file per
  route. Tailwind for styling, Framer Motion for transitions.
- **Fail-closed auth.** `CB_API_KEY` (32-byte URL-safe random) + bearer
  header. `THIRSTY_AI_REQUIRE_AUTH=1` makes startup refuse to boot without
  it. `hmac.compare_digest` for timing-safe verification.
- **Fail-closed persistence.** `THIRSTY_AI_REQUIRE_MONGO=1` makes startup
  refuse to boot without a real Mongo. The in-memory stub stays for tests
  only.
- **Deterministic RAG.** 32-dim hash-based vectors, deterministic cosine
  retrieval. No external embedding service required.
- **Rate-limited and size-capped.** 60 req/min/key, 1 MiB body cap
  (configurable), Pydantic `max_length` on every free-text field.
- **Ed25519 release signing.** Key generated locally per machine; private
  key never enters the repo; public key at `release/signing-public-key.pem`.
- **Reproducible release artifact.** CycloneDX SBOM, package manifest,
  Ed25519 signature under `release/`.
- **Container-hardened.** Non-root UID, `no-new-privileges`, `read_only: true`
  with a small tmpfs for `/tmp`, all capabilities dropped except
  `NET_BIND_SERVICE`.
- **GitHub Action drop-in.** `rust-auditor/.github/workflows/commander-audit.yml`
  audits any repo automatically.

---

## Diagrams

All diagrams live in **`docs/DIAGRAMS.md`**. That file is the single source
of visual truth. This README links into it; it does not duplicate it.

| Diagram | What it shows |
|---|---|
| §1 — **System topology** | Browser → reverse proxy → frontend nginx → backend → Mongo + Ollama |
| §2 — **Request flow** | A click in the browser to a row in Mongo (auth, rate limit, validation, response) |
| §3 — **Chat / RAG pipeline** | User question → embed → retrieve → prompt → Ollama → answer |
| §4 — **Audit pipeline** | Run audit → hash-linked append-only log → sign → PDF |
| §5 — **Deploy paths** | Railway / Vercel+Render / Fly / VPS at a glance |
| §6 — **Trust boundaries** | The four boundaries from `THREAT_MODEL.md`, drawn |
| §7 — **Release artifact** | Source → SBOM → package → signature |

Open `docs/DIAGRAMS.md` to see them.

---

## Installation Methods

There are three installation tracks. Pick the one that matches what you
want to do.

| Track | Audience | Time to first page | What you get |
|---|---|---|---|
| **A. Local dev** (Python venv + npm) | Engineers iterating on the code | ~10 min | Hot-reload backend on `:8001`, hot-reload frontend on `:3000` |
| **B. Local all-in-one** (Docker Compose) | Anyone who wants the whole stack up with one command | ~5 min | Containers for backend, frontend, Mongo on one host |
| **C. Production deploy** | Operators exposing the service | ~30 min | TLS-terminated, fail-closed, with the four paths in `DEPLOY.md` |

The full step-by-step for all three tracks — including Windows, macOS, and
Linux — is in **`docs/INSTALL.md`**. The short version is below.

### Track A — Local dev (10 minutes)

Prereqs: Python 3.11+, Node 18+, Ollama running locally, one model pulled
(`ollama pull qwen2.5-coder:7b`).

```bash
# Backend
cd backend
pip install -r requirements.txt
cp .env.example .env          # then edit CB_API_KEY
python server.py              # serves on :8001

# Frontend (separate terminal)
cd frontend
npm install
cp .env.example .env
npm start                     # serves on :3000
```

Open http://localhost:3000. The footer shows your entity number. Open
Little Dove or Holli to chat with your local model. No API key required
beyond `CB_API_KEY` for protected endpoints.

### Track B — Docker Compose (5 minutes)

Prereqs: Docker + Docker Compose, Ollama running on the host
(`OLLAMA_HOST=http://host.docker.internal:11434`).

```bash
docker compose up --build
# Backend on :8001, Frontend on :3000, Mongo on :27017
```

The compose file uses `host.docker.internal` so the backend container
can reach the Ollama server on your host. The `/api/health` endpoint
reports `llm_provider: "ollama"` (or `"unavailable"` if Ollama isn't
running).

### Track C — Production deploy

See `DEPLOY.md`. Four paths: Railway (~$5/mo, ~4 min), Vercel + Render
(free tier with managed Mongo), Fly.io (`fly launch && fly deploy`), and
a self-managed VPS (Ubuntu 22.04+ with Docker). All four converge on the
same backend image and the same env-var contract.

After every deploy, run the preflight before exposing the service:

```bash
docker compose exec backend python -m thirsty_ai_builder_backend.preflight
# expected: PASS: thirsty-ai-builder production preflight
```

---

## Configuration Reference

Every knob the Builder reads from the environment. Set them in
`backend/.env` for local dev, or in your platform's secret store for
production.

| Variable | Default | Required for prod? | What it does |
|---|---|---|---|
| `CB_API_KEY` | *(none)* | **Yes** | 32-byte URL-safe bearer token for protected endpoints |
| `THIRSTY_AI_REQUIRE_AUTH` | `0` | **Yes (set to `1`)** | Fail-closed at startup if `CB_API_KEY` is missing |
| `MONGO_URL` | in-memory stub | **Yes** | MongoDB connection string |
| `THIRSTY_AI_REQUIRE_MONGO` | `0` | **Yes (set to `1`)** | Fail-closed at startup if Mongo is unreachable |
| `DB_NAME` | `thirsty_ai_builder` | No | Mongo database name |
| `OLLAMA_HOST` | `http://127.0.0.1:11434` | No | Where the backend looks for the local model |
| `OLLAMA_MODEL` | `qwen2.5-coder:7b` | No | Which model to use for chat / RAG / Marketing |
| `CORS_ORIGINS` | `http://localhost:3000` | Yes | Comma-separated allowed origins; never use `*` with credentials |
| `THIRSTY_AI_TRUST_PROXY` | `0` | Only behind a trusted proxy | Lets the app trust `X-Forwarded-For` from a known reverse proxy |
| `THIRSTY_AI_MAX_REQUEST_BYTES` | `1048576` (1 MiB) | No | Body size cap |
| `THIRSTY_AI_REQUIRE_OLLAMA` | `0` | No (set to `1` to opt in) | Fail-closed at startup if Ollama is unreachable |

If `OLLAMA_HOST` points at an empty port or Ollama is down, the chat
endpoints return **HTTP 503** with an actionable message ("start it with
`ollama serve` and pull a model with `ollama pull ...`"). The rest of the
product keeps working.

---

## Daily Operations

### Add a tool to the App Store

Edit `backend/thirsty_ai_builder_backend/app_store.py` and append a dict to
`SEED_TOOLS`. The UI picks the new row up on the next request — no rebuild
required.

### Swap the AI model

```bash
ollama pull mistral             # or llama3.2, codestral, phi3, …
# in backend/.env:
OLLAMA_MODEL=mistral
# restart the backend
```

The Builder uses that model for all chat endpoints (Little Dove, Holli,
Marketing, RAG answer). RAG embeddings stay deterministic in-process.

### Whitelabel for a client

- `frontend/src/components/ThirstyLogo.jsx` — swap this SVG for the
  client's mark.
- `frontend/tailwind.config.js` — change the palette.
- `frontend/src/index.css` — mirror the palette change.
- `OWNERSHIP.md` and `OWNER_HANDOFF.md` — replace the entity block with
  the client's.

### Run an audit and download the signed PDF

Open **Commander** in the UI, click **Run audit**. The audit runs the
canonical `verify_all.py` gate, hashes the body, signs the PDF with
Ed25519, embeds your entity number and the SHA-256 attestation, and
serves the file as a download. The PDF is verifiable against
`release/signing-public-key.pem`.

### Gate any GitHub repo with the Commander

Copy `rust-auditor/.github/workflows/commander-audit.yml` into any
GitHub repository. Add a `CB_API` and `CB_API_KEY` secret. Every PR
gets audited automatically and the workflow fails closed on a denial.

---

## Deploy to Production

Four paths, all documented in `DEPLOY.md`:

1. **Railway** — ~$5/month, ~4 minutes. Push the repo, set env vars, hit
   deploy. Ollama on a $5 VPS reachable over Tailscale / WireGuard / SSH.
2. **Vercel + Render** — free tier. Frontend on Vercel (CRA preset),
   backend on Render (Docker), Mongo on Atlas free.
3. **Fly.io** — `fly launch && fly deploy`. Backed by `fly.toml` if
   present, otherwise the bundled `backend/Dockerfile`.
4. **VPS** — your own Ubuntu 22.04+ box. Docker + Docker Compose +
   Ollama on the host. Caddy or nginx in front for TLS.

The hardening checklist in `SECURITY.md` applies to all four paths. The
short version: terminate TLS at a reverse proxy, set
`THIRSTY_AI_REQUIRE_AUTH=1` and `THIRSTY_AI_REQUIRE_MONGO=1`, run the
preflight, and never expose Mongo or Ollama to the public internet.

---

## Security & Threat Model

- `SECURITY.md` — supported versions, reporting channel (karrick1995@gmail.com,
  subject prefix `[security]`), 72-hour acknowledgement, 90-day disclosure
  window, and a 12-item hardening checklist for self-hosted deployments.
- `THREAT_MODEL.md` — assets, adversaries, four trust boundaries, and the
  top ten threats (T1 CORS, T2 unbounded body, T3 token brute-force, T4 LLM
  DoS, T5 prompt injection, T6 audit forgery, T7 info disclosure, T8 silent
  Mongo fallback, T9 dependency CVEs, T10 container breakout) with the
  mitigation for each.
- `HOSTED_OLLAMA.md` — operator runbook for hosting Ollama off-box
  (Tailscale, WireGuard, SSH tunnel, hardening, backups, monitoring).

Cryptography summary: Ed25519 release signing via PyCA; opaque 32-byte
random auth tokens (not JWTs) with `hmac.compare_digest`; TLS terminated
at the reverse proxy; the backend speaks plain HTTP inside the trust
boundary. The signing private key is generated locally per machine and
never enters the repo.

---

## Ownership, License, and IP

This product is registered to **Thirsty's Projects LLC** (Entity
#14694374-0160). Principal office: 1450 South West Temple Street, A402,
Salt Lake City, UT 84115-5203. Registered agent: Entity Protect
Registered Agent Services LLC, 169 W 2710 S Circle, STE 202A-65, Saint
George, UT 84790-7205. Contact: karrick1995@gmail.com.

| Where | What it proves |
|---|---|
| `LICENSE` | Proprietary license, your name, LLC, entity #, principal office, registered agent |
| `OWNERSHIP.md` | Full filing details + registered-asset inventory |
| `GET /api/ownership` | The canonical ownership block, returned as JSON |
| `/about` page | The public ownership panel in the UI |
| Footer, every page | © line with entity # + Salt Lake City address |
| Every signed PDF | Letterhead + entity # + SHA-256 attestation + signature block |

All rights reserved. No third party may sublicense, resell, fork for
redistribution, or remove the attribution. Independent developers may
be engaged under written agreement with the owner.

---

## Pointers to the Rest of the Docs

| Document | Read it when you want to … |
|---|---|
| `docs/DIAGRAMS.md` | … see the system, request flow, pipelines, or deploy paths as pictures. |
| `docs/INSTALL.md` | … install on Windows, macOS, or Linux, in dev or Docker or production. |
| `DEPLOY.md` | … ship to Railway, Vercel+Render, Fly, or a VPS. |
| `SECURITY.md` | … report a vulnerability or harden a self-hosted deployment. |
| `THREAT_MODEL.md` | … understand the trust boundaries and the top ten threats. |
| `HOSTED_OLLAMA.md` | … run Ollama on a separate host (Tailscale / WireGuard / SSH). |
| `OWNER_HANDOFF.md` | … get the single-sheet operator hand-off. |
| `OWNERSHIP.md` | … see the registration + IP inventory. |
| `CHANGELOG.md` | … see what changed in each release. |
| `design_guidelines.json` | … see the design system (colors, type, spacing, voice). |
| `release/` | … see the SBOM, package manifest, and Ed25519 signature for the current release. |

---

## FAQ

**Do I need an OpenAI / Anthropic API key?**
No. The Builder talks to a local Ollama server. If you have a key, you
do not need to use it here.

**Do I need a cloud account?**
No. Track A and Track B above run entirely on your machine. Track C
(Railway / Vercel+Render / Fly / VPS) is what you use when you want to
expose the service — and the deployment guide documents a free path.

**What if Ollama isn't running?**
The chat endpoints return HTTP 503 with a clear error. The rest of the
app — Commander, App Store, Business Manager, About, Architecture — keeps
working. Set `THIRSTY_AI_REQUIRE_OLLAMA=1` if you want startup to fail
closed instead.

**What models can I use?**
Any model Ollama can serve. Default is `qwen2.5-coder:7b` (5 GB on disk,
~10 tok/s on CPU). `llama3.2`, `codestral`, `phi3`, `mistral`, and
anything else in the Ollama library also work.

**Can a non-engineer use this?**
Yes — once it's installed. The 11 pages are designed to be operated by
a non-engineer. The install + Ollama model pull is the only step that
needs a terminal.

**Can a developer maintain this?**
Yes — any full-stack dev with FastAPI + React + MongoDB experience can
maintain it in a day. The whole backend is one file (`server.py`); each
frontend page is one file.

**Is it multi-tenant?**
No. It is single-tenant by design. One operator per deployment. If you
need multi-tenant, that is a different product.

**How do I report a security issue?**
Email karrick1995@gmail.com with subject prefix `[security]`. See
`SECURITY.md` for the full disclosure policy (72-hour ack, 90-day window).

---

© 2026 Jeremy Karrick / Thirsty's Projects LLC. Entity #14694374-0160. All rights reserved.
1450 South West Temple Street, A402, Salt Lake City, UT 84115-5203.
