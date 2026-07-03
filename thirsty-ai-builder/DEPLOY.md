# Deploy

Four deploy paths. Pick one.

## 1. Railway (~$5/month, ~4 minutes)

1. Sign in at https://railway.app.
2. **New Project → Deploy from GitHub** (push this folder to a GitHub repo first, or drag the `docker-compose.yml` in).
3. Railway detects the compose file and shows 3 services: `mongo`, `backend`, `frontend`.
4. On the `backend` service, click **Variables** and add:
   ```
   OLLAMA_HOST=http://host.docker.internal:11434
   OLLAMA_MODEL=qwen2.5-coder:7b
   MONGO_URL=mongodb://mongo:27017
   THIRSTY_AI_REQUIRE_MONGO=1
   DB_NAME=thirsty_ai_builder
   CORS_ORIGINS=https://<your-frontend-domain>
   CB_API_KEY=<32-byte-url-safe-token-from-secret-manager>
   THIRSTY_AI_REQUIRE_AUTH=1
   ```
5. On the `frontend` service, add:
   ```
   REACT_APP_BACKEND_URL=https://<your-backend>.up.railway.app
   ```
6. Hit **Deploy**. Live in ~4 minutes.

**Ollama on Railway:** Railway doesn't ship Ollama as a managed service. Run Ollama on a $5/month VPS and point `OLLAMA_HOST` at its public URL over Tailscale / WireGuard / SSH tunnel. For a no-tunnel path, the same Ollama instance on a VPS can serve the Railway backend.

## 2. Vercel + Render (free)

- **Frontend → Vercel** (Create React App preset; the included `frontend/` is CRA-shaped).
- **Backend → Render** (Docker service; point at the included `backend/Dockerfile`).
- **Mongo → MongoDB Atlas free tier**.
- Set `MONGO_URL` on Render to the Atlas connection string.
- Set `REACT_APP_BACKEND_URL` on Vercel to the Render backend URL.
- Cost: $0.

## 3. Fly.io

```bash
fly launch        # in the repo root
fly secrets set CB_API_KEY=<32-byte-url-safe-token>
fly secrets set THIRSTY_AI_REQUIRE_AUTH=1
fly secrets set MONGO_URL=mongodb://<user>:<password>@<host>:27017/<db>
fly secrets set THIRSTY_AI_REQUIRE_MONGO=1
fly deploy
```

Fly picks up the `fly.toml` if present; otherwise it'll detect the
`Dockerfile` in `backend/`. The frontend can be deployed as a static
site via `fly static` or to Vercel.

## 4. VPS (your own box)

```bash
# On a fresh Ubuntu 22.04+ box
sudo apt update && sudo apt install -y docker.io docker-compose
# Install Ollama on the host (not in a container) so all data stays
# local. See https://ollama.com/download.
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5-coder:7b

git clone <this-repo> thirsty-ai-builder
cd thirsty-ai-builder
cp backend/.env.example backend/.env
nano backend/.env   # OLLAMA_HOST stays at http://127.0.0.1:11434
docker compose up -d
```

Point a reverse proxy (Caddy, nginx) at the frontend on
`127.0.0.1:3000`. The backend is not published to the host; the
frontend nginx proxies `/api/*` to the backend on the compose network.
For production, terminate TLS at the proxy.

## From your iPhone (no laptop needed)

- **Railway** and **Vercel** both let you deploy entirely from a
  mobile browser.
- Push the repo to GitHub via the GitHub iOS app, then import it in
  Railway/Vercel.
- Add env vars from the mobile dashboard. Hit deploy.

## After deploy

Run the production preflight before exposing the service:

```bash
docker compose exec backend python -m thirsty_ai_builder_backend.preflight
# expected: PASS: thirsty-ai-builder production preflight
```

Smoke-test:

```bash
curl https://<your-frontend-domain>/api/health
# expected: {"status":"ok","product":"ThirstyAi Builder",...}
```

Visit the URL in your browser. The footer should display the entity
number on every page.
