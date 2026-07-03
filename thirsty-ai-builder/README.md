# ThirstyAi Builder

**Owner-attested, governance-first, dep-light AI builder.**

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

## What you need before deploying

One of these LLM keys:

- **Universal Emergent key** — `EMERGENT_LLM_KEY` (works for OpenAI, Anthropic, Gemini in one key)
- **Your own Anthropic key** — `ANTHROPIC_API_KEY` from console.anthropic.com

## Quick start (local)

```bash
# Backend
cd backend
pip install -r requirements.txt
cp .env.example .env   # add your LLM key
python server.py       # serves on :8001

# Frontend (separate terminal)
cd frontend
yarn install           # or npm install
cp .env.example .env
yarn start             # serves on :3000
```

## Quick start (Docker)

```bash
docker compose up --build
# Backend on :8001, Frontend on :3000, Mongo on :27017
```

## What ships in the 11-page UI

- **Home** — landing + system status
- **Commander** — run audits, list past audits, download signed PDFs
- **Little Dove** — quiet conversational assistant
- **Holli** — operations assistant with audit-logged replies
- **Architecture** — system topology
- **App Store** — installable tools, one row per tool
- **Business Manager** — clients, invoices, deliverables (CRUD)
- **Socials** — multi-channel post queue (Twitter, LinkedIn, Mastodon, Bluesky)
- **Marketing** — copy generator with brand-voice presets
- **RAG** — embed + query with deterministic cosine retrieval
- **About** — ownership block + IP inventory

## Files you'll edit most

- `backend/server.py` — every API endpoint lives here
- `backend/thirsty_ai_builder_backend/app_store.py` — `SEED_TOOLS` array; the UI picks up new rows automatically
- `frontend/src/components/ThirstyLogo.jsx` — swap this SVG for your official logo when ready
- `frontend/src/index.css` — palette + tokens (mirror of `design_guidelines.json`)

## Ownership and rights

This product is registered to **Thirsty's Projects LLC** (Entity
#14694374-0160). All rights reserved. See `LICENSE` and `OWNERSHIP.md`.
The `/api/ownership` endpoint and the `/about` page return the
canonical ownership block; the UI footer renders it on every page;
every signed PDF embeds it with an SHA-256 attestation.
