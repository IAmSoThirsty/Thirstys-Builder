# ThirstyAi Builder — Install

The full install matrix. Three tracks × three operating systems = nine
install paths. Pick the one that matches what you want to do and the
machine you are on.

| Track | Audience | Time to first page | What you get |
|---|---|---|---|
| **A. Local dev** (Python venv + npm) | Engineers iterating on the code | ~10 min | Hot-reload backend on `:8001`, hot-reload frontend on `:3000` |
| **B. Local all-in-one** (Docker Compose) | Anyone who wants the whole stack up with one command | ~5 min | Containers for backend, frontend, Mongo on one host |
| **C. Production deploy** | Operators exposing the service | ~30 min | TLS-terminated, fail-closed, four paths in `DEPLOY.md` |

```
                  ┌──────────────────────────────────────────┐
                  │  Pick an OS row, then a Track column.    │
                  └──────────────────────────────────────────┘

                            A. Local dev    B. Docker    C. Production
                            ────────────    ─────────    ─────────────
   Windows                  §1.A            §1.B          §1.C
   macOS                    §2.A            §2.B          §2.C
   Linux (Ubuntu 22.04+)    §3.A            §3.B          §3.C

   All tracks: §4 — first-run checks
   All tracks: §5 — uninstall / reset
```

> **Before you start, all tracks need one thing: Ollama running on the
> same host, with one model pulled.** §0 has the 5-minute Ollama install
> for every OS. Without Ollama, the chat endpoints return 503 (which is
> honest behaviour, not a bug).

---

## §0. Install Ollama (all tracks, all OSes)

The ThirstyAi Builder talks to a local Ollama server. The default URL is
`http://127.0.0.1:11434`. The default model is `qwen2.5-coder:7b`
(~5 GB on disk). Pick your OS.

### §0.1 Windows

```powershell
# 1. Download + run the installer
#    https://ollama.com/download  (run the .exe)

# 2. Ollama is registered as a Windows service and starts automatically.
#    Confirm it is up:
ollama --version

# 3. Pull the default model
ollama pull qwen2.5-coder:7b

# 4. (Optional) Pin the model in a persistent env var
[Environment]::SetEnvironmentVariable("OLLAMA_MODEL", "qwen2.5-coder:7b", "User")
```

If you want Ollama to bind somewhere other than loopback (you don't, by
default), see `../HOSTED_OLLAMA.md`.

### §0.2 macOS

```bash
# 1. Download the .dmg
#    https://ollama.com/download
#    Drag to Applications, launch. Menu-bar icon appears.

# 2. Confirm
ollama --version

# 3. Pull the default model
ollama pull qwen2.5-coder:7b

# 4. (Optional) pin the model
echo 'export OLLAMA_MODEL=qwen2.5-coder:7b' >> ~/.zshrc
source ~/.zshrc
```

Apple Silicon (M1/M2/M3/M4) is supported by upstream Ollama and uses
Metal under the hood.

### §0.3 Linux (Ubuntu 22.04+ / Debian 12+)

```bash
# 1. Install
curl -fsSL https://ollama.com/install.sh | sh

# 2. Confirm
ollama --version
systemctl status ollama

# 3. Pull the default model
ollama pull qwen2.5-coder:7b

# 4. (Optional) pin the model
echo 'export OLLAMA_MODEL=qwen2.5-coder:7b' >> ~/.bashrc
source ~/.bashrc
```

The upstream installer writes `/etc/systemd/system/ollama.service` with
loose defaults. For a hardened unit, see `../HOSTED_OLLAMA.md` §2.

### §0.4 Smoke-test Ollama from any OS

```bash
curl http://127.0.0.1:11434/api/tags
# expected: JSON with one entry per pulled model
```

If that returns a model list, the Builder will be able to chat.

---

## §1. Windows

### §1.A — Local dev (Python venv + npm)

Prereqs: Python 3.11+, Node.js 18+, Ollama running (§0.1).

```powershell
# 1. Clone
git clone <this-repo> thirsty-ai-builder
cd thirsty-ai-builder

# 2. Backend
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# Open .env in Notepad, set CB_API_KEY to a fresh 32-byte random string.
# PowerShell: $key = [Convert]::ToBase64String((1..32|%{Get-Random -Max 256})) ; "CB_API_KEY=$key" | Out-File -Append .env
python server.py              # serves on :8001

# 3. Frontend (separate terminal)
cd ..\frontend
npm install
copy .env.example .env
npm start                     # serves on :3000
```

Open http://localhost:3000.

### §1.B — Docker Compose (local all-in-one)

Prereqs: Docker Desktop, Ollama running (§0.1).

```powershell
git clone <this-repo> thirsty-ai-builder
cd thirsty-ai-builder
copy backend\.env.example backend\.env
# Set CB_API_KEY in backend\.env
docker compose up --build
# Backend on :8001, Frontend on :3000, Mongo on :27017
```

The compose file uses `host.docker.internal` so the backend container
can reach Ollama on the host.

### §1.C — Production on Windows

Production deploys of a public-facing service are **not** recommended on
Windows. The Docker path (§1.B) works locally; for production, deploy
to a Linux host using `../DEPLOY.md`. If you must run production on
Windows, the closest equivalent is:

1. Use **Docker Desktop with WSL2** (this is the only path with a
   supported filesystem, a real TUN/TAP for tunnels, and a sane
   resource model).
2. Run Ollama on the **Windows host** (not in WSL) and point the WSL
   backend at it over the WSL2 loopback: `OLLAMA_HOST=http://$(hostname).local:11434`
   or use `host.docker.internal` from inside WSL.
3. Terminate TLS with **Caddy on Windows** (`caddy.exe reverse-proxy`).
4. Set `THIRSTY_AI_REQUIRE_AUTH=1` and `THIRSTY_AI_REQUIRE_MONGO=1`.

For everything beyond a local install, use a Linux host.

---

## §2. macOS

### §2.A — Local dev (Python venv + npm)

Prereqs: Python 3.11+ (`brew install python@3.11`), Node.js 18+
(`brew install node`), Ollama running (§0.2).

```bash
git clone <this-repo> thirsty-ai-builder
cd thirsty-ai-builder

# Backend
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Set CB_API_KEY: python -c "import secrets; print(secrets.token_urlsafe(32))"
python server.py              # serves on :8001

# Frontend (separate terminal)
cd ../frontend
npm install
cp .env.example .env
npm start                     # serves on :3000
```

Open http://localhost:3000.

### §2.B — Docker Compose (local all-in-one)

Prereqs: Docker Desktop for Mac, Ollama running (§0.2).

```bash
git clone <this-repo> thirsty-ai-builder
cd thirsty-ai-builder
cp backend/.env.example backend/.env
# Set CB_API_KEY in backend/.env
docker compose up --build
```

`host.docker.internal` works out of the box on Docker Desktop for Mac.

### §2.C — Production on macOS

macOS is supported as a **single-user** production host (e.g. a Mac mini
in a closet) using the Docker path (§2.B) + **Caddy for macOS** for TLS
termination. The hardening checklist in `../SECURITY.md` applies
unchanged.

For multi-user public production, use a Linux host. `../DEPLOY.md` has
the four paths.

---

## §3. Linux (Ubuntu 22.04+ / Debian 12+)

### §3.A — Local dev (Python venv + npm)

Prereqs: `sudo apt install -y python3.11 python3.11-venv nodejs npm`,
Ollama running (§0.3).

```bash
git clone <this-repo> thirsty-ai-builder
cd thirsty-ai-builder

# Backend
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Set CB_API_KEY: python -c "import secrets; print(secrets.token_urlsafe(32))"
python server.py              # serves on :8001

# Frontend (separate terminal)
cd ../frontend
npm install
cp .env.example .env
npm start                     # serves on :3000
```

Open http://localhost:3000.

### §3.B — Docker Compose (local all-in-one)

Prereqs: Docker + Docker Compose (`sudo apt install -y docker.io
docker-compose` or the convenience script at
https://get.docker.com), Ollama running (§0.3).

```bash
git clone <this-repo> thirsty-ai-builder
cd thirsty-ai-builder
cp backend/.env.example backend/.env
# Set CB_API_KEY in backend/.env
docker compose up --build
```

On Linux, the compose file uses `host.docker.internal` only if you add
it to the daemon's `extra_hosts` — by default the backend can reach the
host Ollama via `http://172.17.0.1:11434` (the docker bridge gateway)
or you can set `OLLAMA_HOST=http://127.0.0.1:11434` and add
`network_mode: host` to the backend service. The shipped compose file
documents both options inline.

### §3.C — Production on a Linux VPS

This is the canonical production path. The full version is in
`../DEPLOY.md` §4. The 10-minute version:

```bash
# On a fresh Ubuntu 22.04+ box
sudo apt update && sudo apt install -y docker.io docker-compose
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5-coder:7b

git clone <this-repo> thirsty-ai-builder
cd thirsty-ai-builder
cp backend/.env.example backend/.env
# Set CB_API_KEY, THIRSTY_AI_REQUIRE_AUTH=1, THIRSTY_AI_REQUIRE_MONGO=1
# in backend/.env
docker compose up -d

# Reverse proxy: Caddy or nginx
sudo apt install -y caddy
# Use the shipped Caddyfile (or write your own):
sudo cp deploy/Caddyfile /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

After deployment, run the preflight (§4.2) before exposing the service.

---

## §4. First-run checks (all tracks, all OSes)

### §4.1 — Confirm the Builder is up

```bash
curl http://localhost:8001/api/health
# expected:
# {"status":"ok","product":"ThirstyAi Builder","version":"1.0.0",
#  "llm_provider":"ollama","ollama":"127.0.0.1:11434",
#  "model":"qwen2.5-coder:7b"}
```

If `llm_provider` reads `"unavailable"`, the backend can't reach
Ollama. Walk the network:

```bash
curl -v http://127.0.0.1:11434/api/tags
# -v shows DNS, TCP, HTTP. Stop at the first failure.
```

### §4.2 — Production preflight (Track C only)

Run this **before exposing the service**:

```bash
docker compose exec backend python -m thirsty_ai_builder_backend.preflight
# expected: PASS: thirsty-ai-builder production preflight
```

The preflight refuses to pass if `CB_API_KEY` is missing, short, or
placeholder-looking, if Mongo is unreachable, or if required
env vars are absent.

### §4.3 — Confirm auth works

```bash
# With the right key → 200
curl -H "Authorization: Bearer <CB_API_KEY>" http://localhost:8001/api/ownership

# Without → 401
curl http://localhost:8001/api/ownership
```

### §4.4 — Confirm the SPA renders

Open http://localhost:3000 (or the production URL) in a browser. The
**footer on every page** should show:

> © 2026 Jeremy Karrick / Thirsty's Projects LLC. Entity #14694374-0160. All rights reserved.

If the footer is missing, the build is wrong. If the entity number
doesn't match, somebody edited `OWNERSHIP.md` — put it back.

### §4.5 — Confirm Ollama is wired

Open **Little Dove** in the UI and send the message "Reply with the
single word READY." You should get a short answer within a few seconds.
The first call after a cold start takes longer (model load); subsequent
calls are sub-second.

---

## §5. Uninstall / reset

### §5.1 — Stop the running stack

```bash
# Track A
# Stop the backend (Ctrl+C in its terminal)
# Stop the frontend (Ctrl+C in its terminal)

# Track B and C
docker compose down            # stop and remove containers, keep volumes
docker compose down -v         # stop, remove containers AND volumes (wipes Mongo)
```

### §5.2 — Remove the local checkout

```bash
cd ..
rm -rf thirsty-ai-builder      # macOS / Linux
Remove-Item -Recurse -Force thirsty-ai-builder   # Windows PowerShell
```

### §5.3 — Remove the Ollama model (free 5 GB)

```bash
ollama rm qwen2.5-coder:7b
```

### §5.4 — Wipe everything (nuclear)

```bash
# Remove the Builder repo (see §5.2)
# Remove Ollama
ollama serve --help            # confirm path; or:
sudo systemctl stop ollama
sudo systemctl disable ollama
sudo rm /etc/systemd/system/ollama.service
sudo rm -rf /usr/local/bin/ollama /usr/local/lib/ollama /var/lib/ollama
sudo userdel ollama
# On macOS: drag Ollama.app to the Trash.
# On Windows: Settings → Apps → Ollama → Uninstall.
```

No remote state is held by the operator. There is no cloud account to
close. The release artifact under `release/` is optional and removable
with `rm -rf release/`.

---

## See also

- `../README.md` — the 30-second pitch + table of contents. (This file
  lives at `thirsty-ai-builder/README.md`; the relative path works when
  the docs are read from a checkout.)
- `DIAGRAMS.md` — the system, request, pipeline, deploy, and
  trust-boundary diagrams (sibling of this file).
- `../DEPLOY.md` — the four production deploy paths in full.
- `../SECURITY.md` — hardening checklist for self-hosted deployments.
- `../HOSTED_OLLAMA.md` — full runbook for hosting Ollama on a
  separate host.
