# ThirstyAi Builder

**Owner-attested, governance-first, dep-light AI builder. Runs entirely on your machine.**

A single-binary deployable for the ThirstyAi product surface: 11-page
React UI, FastAPI backend, MongoDB persistence, Rust CI auditor,
in-process RAG, and a Commander that signs every audit as a PDF.

```
thirsty-ai-builder/
├── backend/                 ← FastAPI (Python) — all API endpoints
├── frontend/                ← React + Tailwind + Framer Motion — the 11-page UI
├── rust-auditor/            ← Rust CLI that gates CI against the Commander
│   └── .github/workflows/commander-audit.yml   ← drop-in GitHub Action
├── docker-compose.yml       ← one command to run the whole thing
├── README.md                ← what this is
├── DEPLOY.md                ← 4 deploy paths (Railway, Vercel+Render, Fly, VPS)
├── LICENSE                  ← your proprietary license
├── OWNERSHIP.md             ← your registration + IP inventory
├── OWNER_HANDOFF.md         ← operator hand-off
└── design_guidelines.json   ← the design system
```

## What you need before running

**A local Ollama server.** That's it. No API keys, no cloud accounts, no
monthly bills.

```bash
# Install Ollama (one time)
# Windows / macOS: https://ollama.com/download
# Linux: curl -fsSL https://ollama.com/install.sh | sh

# Start the server (it auto-runs on Windows after install)
ollama serve

# Pull a model (one time, ~5 GB)
ollama pull qwen2.5-coder:7b
```

The ThirstyAi Builder talks to Ollama at `http://127.0.0.1:11434` by
default. Set `OLLAMA_HOST` to override (e.g. when running inside
Docker). Set `OLLAMA_MODEL` to pick a different model (default
`qwen2.5-coder:7b`).

## Quick start (local)

```bash
# Backend
cd backend
pip install -r requirements.txt
cp .env.example .env
python server.py       # serves on :8001

# Frontend (separate terminal)
cd frontend
npm install
cp .env.example .env
npm start              # serves on :3000
```

The browser opens the 11-page UI. The footer on every page shows your
entity number. The About page shows the full ownership block. Open
Little Dove or Holli in the browser to chat with your local Ollama
model — no API key required.

## Quick start (Docker)

```bash
docker compose up --build
# Backend on :8001, Frontend on :3000, Mongo on :27017
```

The compose file mounts `OLLAMA_HOST=http://host.docker.internal:11434`
so the container can reach the Ollama server on your host. The
backend's `/api/health` endpoint reports `llm_provider: "ollama"` (or
`"unavailable"` if Ollama isn't running).

## What ships in the 11-page UI

- **Home** — landing + system status (provider, version)
- **Commander** — run audits, list past audits, download signed PDFs
- **Little Dove** — quiet conversational assistant (local Ollama)
- **Holli** — operations assistant (local Ollama)
- **Architecture** — system topology
- **App Store** — installable tools, one row per tool
- **Business Manager** — clients, invoices, deliverables (CRUD)
- **Socials** — multi-channel post queue (Twitter, LinkedIn, Mastodon, Bluesky)
- **Marketing** — copy generator with brand-voice presets (local Ollama)
- **RAG** — embed + query with deterministic cosine retrieval (local Ollama for the answer)
- **About** — ownership block + IP inventory

## Files you'll edit most

- `backend/server.py` — every API endpoint lives here
- `backend/thirsty_ai_builder_backend/app_store.py` — `SEED_TOOLS` array; the UI picks up new rows automatically
- `frontend/src/components/ThirstyLogo.jsx` — swap this SVG for your official logo when ready
- `frontend/src/index.css` — palette + tokens (mirror of `design_guidelines.json`)

## Models you can use

Any model Ollama can serve. Pull a code model, a chat model, a vision
model, whatever you want:

```bash
ollama pull llama3.2
ollama pull codestral
ollama pull phi3
ollama pull mistral
```

Set `OLLAMA_MODEL=mistral` in `backend/.env` and restart. The builder
will use that model for all chat endpoints (Dove, Holli, Marketing, RAG).

If the model you ask for isn't in your local Ollama, the builder
falls back to the first model that is. If Ollama isn't running, the
chat endpoints return `503` with an actionable error message ("start
it with `ollama serve` and pull a model with `ollama pull ...`").

## Ownership and rights

This product is registered to **Thirsty's Projects LLC** (Entity
#14694374-0160). All rights reserved. See `LICENSE` and `OWNERSHIP.md`.
The `/api/ownership` endpoint and the `/about` page return the
canonical ownership block; the UI footer renders it on every page;
every signed PDF embeds it with an SHA-256 attestation.
