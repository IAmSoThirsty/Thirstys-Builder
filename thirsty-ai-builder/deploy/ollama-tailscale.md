# Exposing Ollama over Tailscale

Tailscale is the shortest path from "Ollama on a home/office box" to
"ThirstyAi Builder backend anywhere" without poking firewall holes.
Tailscale gives every machine a stable 100.x.y.z IP on a private
overlay; the Ollama host and the ThirstyAi Builder backend join the
same tailnet, and the backend reaches Ollama by its tailnet IP.

## Install Tailscale on the Ollama host

```bash
# Linux (Ubuntu / Debian)
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
sudo tailscale status    # note the 100.x.y.z IP
```

On macOS / Windows / iOS / Android, install Tailscale from the
vendor's app store and sign in. The "100.x.y.z" IP shows up in the
status panel.

## Bind Ollama to the tailnet

The shipped `deploy/ollama.service` binds to 127.0.0.1, which is
correct for a same-host backend. To expose Ollama on its tailnet IP
instead, override the listen address:

```ini
# Drop into /etc/systemd/system/ollama.service.d/override.conf
[Service]
Environment="OLLAMA_HOST=100.x.y.z"
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl restart ollama
ss -tlnp | grep 11434
# expected: LISTEN  0  128  100.x.y.z:11434  0.0.0.0:*
```

Do NOT bind Ollama to 0.0.0.0. The Tailscale interface (tailscale0)
is enough; binding to 0.0.0.0 exposes the API to every interface
including the public internet if the host has one.

## Install Tailscale on the ThirstyAi Builder backend host

Same install steps. Both machines must show up under the same tailnet
in `tailscale status`.

## Point the backend at the tailnet Ollama

```bash
# On the backend host, in the backend's environment
export OLLAMA_HOST=http://100.x.y.z:11434
export OLLAMA_MODEL=qwen2.5-coder:7b
```

Restart the backend service. The 503 path on every chat endpoint
disappears once the tunnel is up; the `/api/health` route surfaces
the live provider.

## ACLs

By default every Tailscale node can talk to every other node on every
port. Lock that down. In the Tailscale admin console, set an ACL
that allows ONLY:

- Ollama host: receive TCP 11434 from backend tailnet IPs.
- Backend host: send TCP 11434 to the Ollama host.
- Operator devices: same as the backend, so you can `curl` it
  from your laptop for diagnostics.

The shipped `tailscale/acl-example.hujson` is a starter. Replace
`tag:ollama` and `tag:builder-backend` with your real tag names.

## MagicDNS (optional)

Tailscale's MagicDNS gives every machine a stable hostname on the
tailnet. Once enabled, you can use:

```
OLLAMA_HOST=http://ollama-host.tailnet-name.ts.net:11434
```

in the backend's env. That survives the Ollama host's 100.x.y.z IP
rotating (Tailscale IPs are stable, but MagicDNS is more readable
and survives you re-adding the machine).

## Verifying

From the backend host:

```bash
curl http://100.x.y.z:11434/api/tags
# expected: JSON list with "qwen2.5-coder:7b" present
```

If that returns a model list, the backend will pick it up on the next
request and `provider` on the `/api/architecture` page flips to
"ollama (local)".
