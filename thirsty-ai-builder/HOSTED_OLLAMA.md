# Hosted Ollama — Operator Runbook

The ThirstyAI Builder backend talks to a single Ollama server. The
fastest path is a local Ollama on the same machine as the backend
(default `http://127.0.0.1:11434`). This runbook is for the cases
where the backend and Ollama live on different machines: a $5 VPS, a
home server, a GPU box, an office workstation.

The backend is **stateless** about the network path. `OLLAMA_HOST`
is the only knob. Wire anything that reaches the Ollama API to
`OLLAMA_HOST` and the Builder works.

---

## 1. Choose a host

| Use case | Recommended | Cost |
|---|---|---|
| Same machine as the backend | localhost | free |
| Home server, gigabit LAN | Linux box + WireGuard or Tailscale | free beyond power |
| Cloud VM (AWS / Hetzner / DO) | Linux + WireGuard or Tailscale | $5–$40 / month |
| GPU acceleration | Any CUDA 12+ NVIDIA card (8 GB+ VRAM) | hardware cost |
| Apple Silicon | Metal is supported by upstream Ollama | hardware cost |

**Rule of thumb for VRAM:** 7B q4 ≈ 5 GB, 13B q4 ≈ 8 GB, 33B q4 ≈ 20
GB, 70B q4 ≈ 40 GB. The Builder's default model is
`qwen2.5-coder:7b` (5 GB). Larger models work but they take longer
to load and the chat endpoints get slower.

CPU-only works. Expect ~10 tokens/second on a modern 8-core box for
a 7B model. Fine for the Builder's RAG, marketing copy, and chat
endpoints. The Commander audit pipeline is small enough that CPU is
plenty.

## 2. Install Ollama

### Linux (Ubuntu 22.04+, Debian 12+)

```bash
curl -fsSL https://ollama.com/install.sh | sh
# That installs /usr/local/bin/ollama, creates the ollama user,
# drops a default systemd unit, starts the service.
ollama --version
systemctl status ollama
```

The upstream installer writes `/etc/systemd/system/ollama.service`
with very loose defaults. **Replace it** with the hardened unit in
`deploy/ollama.service` of this repo:

```bash
sudo systemctl stop ollama
sudo systemctl disable ollama
sudo cp deploy/ollama.service /etc/systemd/system/ollama.service
sudo systemctl daemon-reload
sudo systemctl enable --now ollama
sudo systemctl status ollama
```

The shipped unit runs Ollama as the `ollama` user with `OLLAMA_MODELS`
under `/var/lib/ollama/models`, binds the API to 127.0.0.1, and
drops every Linux capability that isn't needed.

### macOS

Download the .dmg from https://ollama.com/download, drag to
Applications, launch. The service runs on `127.0.0.1:11434`. No
systemd on macOS; the menu-bar app handles it.

### Windows

Download the installer from https://ollama.com/download, run it.
The service runs on `127.0.0.1:11434` and appears in the system
tray. To swap models:

```powershell
$env:OLLAMA_MODEL = "qwen2.5-coder:7b"
[Environment]::SetEnvironmentVariable("OLLAMA_MODEL", "qwen2.5-coder:7b", "User")
```

## 3. Pull a model

```bash
ollama pull qwen2.5-coder:7b      # default for ThirstyAI Builder
# or
ollama pull llama3.2               # 3B, faster but weaker
ollama pull codestral              # Mistral code-tuned
ollama pull phi3                   # Microsoft, small + fast
ollama pull mistral                # classic 7B
```

The Builder picks the model from `OLLAMA_MODEL` env. Default is
`personal-builder-coder:latest` (the model pinned on the dev box).
Set `OLLAMA_MODEL` on the Builder's backend host to the name of the
model you pulled.

```bash
ollama list
# expected:
# NAME                              ID          SIZE      MODIFIED
# qwen2.5-coder:7b                  xxxxxxxx    4.7 GB    2 minutes ago
```

## 4. Smoke test

```bash
curl http://127.0.0.1:11434/api/tags
# expected: JSON with one entry per pulled model

curl http://127.0.0.1:11434/api/generate -d '{
  "model": "qwen2.5-coder:7b",
  "prompt": "Reply with the single word READY.",
  "stream": false
}'
# expected: JSON with "response":"READY" (or similar short answer)
```

If the second call returns a model answer, the Ollama host is good.

## 5. Point the Builder backend at the Ollama host

In the backend's `.env` (or environment):

```
OLLAMA_HOST=http://<reachable-ip>:11434
OLLAMA_MODEL=qwen2.5-coder:7b
```

Restart the backend. Hit `/api/health`:

```bash
curl http://<backend-host>:8001/api/health
# expected: {"status":"ok", ..., "ollama":"<reachable-ip>:11434", "model":"qwen2.5-coder:7b"}
```

The `/api/architecture` page surfaces the live provider string. If
it reads "ollama (local)" the backend is talking to your hosted
Ollama and the chat endpoints work end-to-end.

## 6. Remote access

The Ollama API is HTTP with **no authentication**. Bind it to
127.0.0.1 and never expose it to the public internet. Reach it from
the backend through one of:

- **Same host** — default. `OLLAMA_HOST=http://127.0.0.1:11434`.
- **Tailnet** — Tailscale. See `deploy/ollama-tailscale.md`.
  Shortest path for a home server. ACL the port.
- **WireGuard tunnel** — see `deploy/ollama-wireguard.conf.example`.
  Use this when you want full control or Tailscale isn't an option
  (compliance, air-gapped network, etc.).
- **SSH tunnel** — quick and dirty. From the backend host:
  ```bash
  ssh -fN -L 127.0.0.1:11434:127.0.0.1:11434 ollama-host
  ```
  Then `OLLAMA_HOST=http://127.0.0.1:11434` on the backend host.
  Survives reconnects poorly; don't rely on it for production.

Bind Ollama to 127.0.0.1 (the shipped unit does this) and let the
tunnel reach localhost on the Ollama host. **Do not** bind Ollama to
0.0.0.0 even with a firewall rule — there is no auth.

## 7. Model storage

Each model is a single GGUF blob. The shipped systemd unit points
`OLLAMA_MODELS` at `/var/lib/ollama/models`. To move it:

```bash
sudo systemctl stop ollama
sudo mkdir -p /srv/ollama/models
sudo chown -R ollama:ollama /srv/ollama
sudo rsync -av /var/lib/ollama/models/ /srv/ollama/models/
# Edit /etc/systemd/system/ollama.service, change OLLAMA_MODELS.
sudo systemctl daemon-reload
sudo systemctl start ollama
ollama list
```

To free space, remove models you don't need:

```bash
ollama rm codestral
```

The Builder only uses one model at a time. Re-pulling is cheap (the
files are content-addressed).

## 8. Backups

Ollama stores three things worth backing up:

- `/var/lib/ollama/models/` — the GGUF blobs. Re-pulling is fine
  but bandwidth is not always. Tar this up nightly.
- `~/.ollama/` (or `/var/lib/ollama/.ollama/`) — per-model Modelfile
  customizations. The Builder doesn't ship any custom Modelfiles, so
  this is usually empty.
- The Builder's own state (Mongo, audit logs) — see the Builder
  deployment guide, separate concern.

A simple cron job is enough:

```bash
# /etc/cron.d/ollama-backup
0 3 * * * root tar -czf /srv/backups/ollama-models-$(date +\%F).tgz -C /var/lib/ollama models
```

## 9. Upgrades

```bash
# Linux
curl -fsSL https://ollama.com/install.sh | sh
# macOS / Windows: re-run the installer from ollama.com

sudo systemctl restart ollama
ollama --version
ollama list
```

Models survive upgrades. After an Ollama major version bump, re-pull
your model to pick up any format changes:

```bash
ollama pull qwen2.5-coder:7b
```

## 10. Monitoring

The Ollama API exposes `/api/tags` and `/api/ps` (running models).
Hit them from any monitoring stack:

```bash
# Health
curl -fs http://127.0.0.1:11434/api/tags

# What is loaded right now
curl -fs http://127.0.0.1:11434/api/ps
```

The Builder's backend hits `/api/tags` on every chat request. A
failure surfaces as HTTP 503 from the chat endpoint and a clear
"Ollama not reachable" line in the backend's stdout. Wire that to
your alerting.

For Prometheus, `ollama_exporter` exists in the community; a 30-line
bash loop hitting `/api/ps` and emitting a gauge is enough for most
operators.

## 11. Security checklist

- [ ] Ollama binds to 127.0.0.1 only. **Never** bind to 0.0.0.0.
- [ ] The Ollama host has no public IP on the API port. If it does,
      close it at the cloud security group / iptables.
- [ ] Backend reaches Ollama over a private tunnel (Tailscale,
      WireGuard, SSH). Not over the public internet.
- [ ] Tailnet / WireGuard is ACL'd to the backend's IP range.
- [ ] `ollama` user has no shell login (`sudo usermod -s /usr/sbin/nologin ollama`).
- [ ] Systemd unit hardening is loaded (`systemctl show ollama | grep -E 'NoNewPrivileges|ProtectSystem'`).
- [ ] Models are pulled over HTTPS from ollama.com. The pull endpoint
      is the only outbound path Ollama needs.
- [ ] OS packages are up to date. `unattended-upgrades` on Ubuntu.
- [ ] Backups run nightly. Tested restore once a quarter.

## 12. Troubleshooting

### Chat endpoint returns 503

The Builder's backend can't reach Ollama. Walk the network:

```bash
# On the backend host
curl -v $OLLAMA_HOST/api/tags
# -v shows DNS, TCP, HTTP. Stop at the first failure.
```

If DNS / TCP fails, the tunnel is down. Restart Tailscale /
WireGuard / the SSH tunnel.

If TCP succeeds but HTTP 4xx/5xx, Ollama is unhappy. Look at its
journal:

```bash
sudo journalctl -u ollama -n 50
```

### Model is slow to load the first time

Cold-load of a 7B model is ~3–8 seconds on a fast disk. The Builder
shows a loading spinner on the chat page. Subsequent calls are
sub-second. If every call is slow, Ollama is being asked to unload
and reload — set `OLLAMA_KEEP_ALIVE` to a long value:

```ini
# /etc/systemd/system/ollama.service.d/override.conf
[Service]
Environment="OLLAMA_KEEP_ALIVE=24h"
```

### Out of disk

```bash
du -sh /var/lib/ollama/models/*
ollama rm <unused-model-name>
```

### Out of memory

A 7B q4 model uses ~5 GB of RAM when loaded. The shipped systemd
unit caps at 32 GB. For larger models, raise `MemoryMax` in
`ollama.service`. If the host is OOMing, drop to a smaller model
(`ollama pull llama3.2`).

### GPU not detected (Linux)

```bash
nvidia-smi
# expected: GPU listed

ollama --version
# expected: 0.x.y or newer
```

Older Ollama builds shipped CUDA libs as a separate package. Modern
Ollama detects CUDA 12.x out of the box. If `nvidia-smi` works but
Ollama still runs on CPU, the `nvidia` driver userland is missing:

```bash
sudo apt install -y nvidia-driver-550    # Ubuntu 22.04
sudo reboot
```

## 13. Pointers

- `deploy/ollama.service` — hardened systemd unit.
- `deploy/ollama-tailscale.md` — Tailscale recipe.
- `deploy/ollama-wireguard.conf.example` — WireGuard template.
- `DEPLOY.md` — the four deploy paths for the Builder itself.
- `OWNER_HANDOFF.md` §3 — "what you need before running" (one Ollama
  server, that's it).
