# Deploy

Four deploy paths. Pick one.

## 1. Railway (~$5/month, ~4 minutes)

1. Sign in at https://railway.app.
2. **New Project → Deploy from GitHub** (push this folder to a GitHub repo first, or drag the `docker-compose.yml` in).
3. Railway detects the compose file and shows 3 services: `mongo`, `backend`, `frontend`.
4. On the `backend` service, click **Variables** and add:
   ```
   EMERGENT_LLM_KEY=sk-emergent-...
   MONGO_URL=mongodb://mongo:27017
   DB_NAME=thirsty_ai_builder
   CORS_ORIGINS=*
   ```
5. On the `frontend` service, add:
   ```
   REACT_APP_BACKEND_URL=https://<your-backend>.up.railway.app
   ```
6. Hit **Deploy**. Live in ~4 minutes.

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
fly secrets set EMERGENT_LLM_KEY=sk-emergent-...
fly secrets set MONGO_URL=mongodb://...
fly deploy
```

Fly picks up the `fly.toml` if present; otherwise it'll detect the
`Dockerfile` in `backend/`. The frontend can be deployed as a static
site via `fly static` or to Vercel.

## 4. VPS (your own box)

```bash
# On a fresh Ubuntu 22.04+ box
sudo apt update && sudo apt install -y docker.io docker-compose
git clone <this-repo> thirsty-ai-builder
cd thirsty-ai-builder
cp backend/.env.example backend/.env
nano backend/.env   # add your LLM key + MONGO_URL
docker compose up -d
```

Point a reverse proxy (Caddy, nginx) at ports 3000 (frontend) and
8001 (backend). For production, terminate TLS at the proxy.

## From your iPhone (no laptop needed)

- **Railway** and **Vercel** both let you deploy entirely from a
  mobile browser.
- Push the repo to GitHub via the GitHub iOS app, then import it in
  Railway/Vercel.
- Add env vars from the mobile dashboard. Hit deploy.

## After deploy

Smoke-test:

```bash
curl https://<your-backend>/api/health
# expected: {"status":"ok","product":"ThirstyAi Builder",...}
```

Visit the URL in your browser. The footer should display the entity
number and the Salt Lake City address on every page.
