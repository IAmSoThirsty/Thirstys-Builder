# ThirstyAI Builder — Owner Hand-Off

**For:** Jeremy Karrick · founderoftp@thirstysprojects.com
**Entity:** Thirsty's Projects LLC · #14694374-0160

This is the single sheet you need. Everything else in the repo is reference.

---

## 1. What you own

You are the sole and exclusive owner of everything in this repository. It is registered to you in:

| Where | What proves ownership |
|---|---|
| `LICENSE` | Proprietary license, your name, LLC, entity #, principal office, registered agent |
| `OWNERSHIP.md` | Full filing details + inventory of registered assets |
| `README.md` | Copyright line on the last page |
| `GET /api/ownership` | Ownership JSON block returned by every deployment |
| `/about` page | Public ownership panel in the UI |
| Footer, every page | © line with entity # |
| Every signed PDF | Letterhead + entity # + SHA-256 attestation + your signature block |

If anyone ever forks or copies this, the ownership block goes with it. That is intentional.

## 2. What is in the repo

The application ships **11 pages** in the UI — same list you'll see in `README.md`:

**Home · Commander · Little Dove · Holli · Architecture · App Store · Business Manager · Socials · Marketing · RAG · About**

```
thirsty-ai-builder/
├── backend/            ← FastAPI (Python) — all API endpoints
├── frontend/           ← React + Tailwind + Framer Motion — the 11-page UI
├── rust-auditor/       ← Rust CLI that gates CI against the Commander
│   └── .github/workflows/commander-audit.yml   ← drop-in GitHub Action
├── docker-compose.yml  ← one command to run the whole thing
├── README.md           ← what this is
├── DEPLOY.md           ← 4 deploy paths (Railway, Vercel+Render, Fly, VPS)
├── LICENSE             ← your proprietary license
├── OWNERSHIP.md        ← your registration + IP inventory
├── OWNER_HANDOFF.md    ← this file
└── design_guidelines.json   ← the design system
```

No `node_modules/`, no compiled artifacts. Fresh install every time.

## 3. What you need before running

**A local Ollama server.** That's the only thing.

```bash
# One time
ollama pull qwen2.5-coder:7b

# Ollama runs as a service on Windows/macOS; on Linux:
ollama serve
```

The ThirstyAI Builder talks to it at `http://127.0.0.1:11434`. Set
`OLLAMA_HOST` to override (e.g. for Docker). Set `OLLAMA_MODEL` to
swap models. If Ollama isn't running, the chat endpoints return a
clear 503 error.

No API keys, no cloud accounts, no monthly bills.

## 4. Deploy

See `DEPLOY.md` for the four paths. Short version: Railway is ~$5/mo
and live in ~4 minutes; the backend, frontend, and Ollama server all
talk to each other over the docker network.

## 5. Edit it in Emergent / Cursor / Windsurf

Open the `thirsty-ai-builder/` folder in your editor of choice.

**Files you'll edit most:**

- `backend/server.py` — every API endpoint lives here
- `backend/thirsty_ai_builder_backend/app_store.py` — add a row to `SEED_TOOLS` to ship a new tool
- `frontend/src/pages/*.jsx` — one file per page
- `frontend/src/components/ThirstyLogo.jsx` — swap this SVG for your official logo

## 6. Hand it to any developer

Any full-stack developer who has used **FastAPI + React + MongoDB** can
maintain this in a single day. The whole backend is one file
(`server.py`). Each frontend page is one file. No hidden framework
magic.

To onboard a dev, share:

- This folder.
- The `LICENSE` (proprietary — they work for you, not the code).
- A signed NDA if you want them under one.

They will need their own local Ollama install to develop against
(`ollama pull qwen2.5-coder:7b`).

## 7. Things you can also do

- **Sell audits** — every Commander audit exports as a **signed PDF** with your letterhead and entity number. Client-ready.
- **Gate any repo** — copy `.github/workflows/commander-audit.yml` from `rust-auditor/` into any GitHub repo, add a `CB_API` and `CB_API_KEY` secret. Every PR gets audited automatically.
- **Extend App Store** — add rows to `SEED_TOOLS` in `backend/thirsty_ai_builder_backend/app_store.py`. The UI picks them up automatically.
- **Whitelabel** — swap `ThirstyLogo.jsx` for a client's mark, change the palette in `frontend/tailwind.config.js`, ship a client-specific edition.

## 8. Models you can swap in

Any model Ollama can serve. The defaults work; if you want to use a
different model, pull it and set `OLLAMA_MODEL`:

```bash
ollama pull llama3.2
ollama pull codestral
ollama pull phi3
ollama pull mistral
```

In `backend/.env`:
```
OLLAMA_MODEL=mistral
```

The builder uses that model for all chat endpoints (Dove, Holli,
Marketing, RAG answer). The Builder still does the embedding lookup
in-process (deterministic 32-dim hash-based vectors) so the RAG
pipeline works without an embedding service.

## 9. Contact & support

- **Product email**: founderoftp@thirstysprojects.com
- **Company**: Thirsty's Projects LLC
- **Registered agent**: Entity Protect Registered Agent Services LLC, 169 W 2710 S Circle, STE 202A-65, Saint George, UT 84790-7205

## 10. Rust auditor build note

The Rust auditor (`rust-auditor/`) builds cleanly on Linux and macOS
out of the box. On Windows, install the Visual Studio C++ build tools
(MSVC) and the rustup `x86_64-pc-windows-msvc` target. The bundled
GitHub Actions workflow uses `ubuntu-latest` where the build is
unattended.
