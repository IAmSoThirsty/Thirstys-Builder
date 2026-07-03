# ThirstyAi Builder — Diagrams

The single source of visual truth for the ThirstyAi Builder. Each section
is one ASCII box-and-arrow picture. Rendered in any monospaced font, no
tooling required.

| § | Diagram | What it shows |
|---|---|---|
| 1 | [System topology](#1-system-topology) | Browser → reverse proxy → frontend nginx → backend → Mongo + Ollama |
| 2 | [Request flow](#2-request-flow-end-to-end) | One click in the browser to one row in Mongo (auth, rate limit, validation, response) |
| 3 | [Chat / RAG pipeline](#3-chat--rag-pipeline) | User question → embed → retrieve → prompt → Ollama → answer |
| 4 | [Audit pipeline](#4-audit-pipeline) | Run audit → hash-linked append-only log → sign → PDF |
| 5 | [Deploy paths](#5-deploy-paths) | Railway / Vercel+Render / Fly / VPS at a glance |
| 6 | [Trust boundaries](#6-trust-boundaries) | The four boundaries from `THREAT_MODEL.md`, drawn |
| 7 | [Release artifact](#7-release-artifact) | Source → SBOM → package → signature |

---

## 1. System topology

What is running, where, and how the parts talk to each other.

```
                          ┌─────────────────────────────┐
                          │        Browser (SPA)        │
                          │  React + Tailwind + Framer  │
                          │  11 pages, 1 file per page  │
                          └──────────────┬──────────────┘
                                         │ HTTPS
                                         │ (single origin)
                                         ▼
                          ┌─────────────────────────────┐
                          │   Reverse proxy (TLS term)  │
                          │   Caddy or nginx + HSTS     │
                          │   public entrypoint :443    │
                          └──────────────┬──────────────┘
                                         │
                                         ▼
                          ┌─────────────────────────────┐
                          │   Frontend (nginx in ctr)   │
                          │  serves static SPA          │
                          │  proxies /api/* to backend  │
                          │  no host port for backend   │
                          └──────────────┬──────────────┘
                                         │ same-origin /api/*
                                         ▼
                          ┌─────────────────────────────┐
                          │   Backend (FastAPI :8001)   │
                          │   one file: server.py       │
                          │   auth, rate-limit,         │
                          │   validation, business      │
                          │   logic, RAG, audit, sign   │
                          └──┬───────────────────────┬──┘
                             │                       │
              compose net   │                       │  Tailscale /
              (internal)    │                       │  WireGuard /
                             ▼                       ▼  SSH tunnel
                ┌──────────────────────┐   ┌──────────────────────┐
                │   MongoDB (in ctr)   │   │   Ollama (loopback)  │
                │   :27017 loopback    │   │   :11434 loopback    │
                │   no host port map   │   │   local model files  │
                │   audit + business   │   │   (no auth on API)   │
                │   data + embeddings  │   │                      │
                └──────────────────────┘   └──────────────────────┘
```

The four trust boundaries drawn around their assets — see §6 for the
explicit boundary list.

---

## 2. Request flow (end to end)

What happens when a logged-in user clicks a button in the SPA and the
server writes a row to Mongo.

```
 Browser                 Reverse proxy         Frontend nginx         Backend (FastAPI)         MongoDB
 ───────                 ─────────────         ──────────────        ─────────────────         ───────
     │                          │                    │                       │                    │
     │  HTTPS GET /api/...      │                    │                       │                    │
     │  Authorization: Bearer   │                    │                       │                    │
     │  <CB_API_KEY>            │                    │                       │                    │
     │─────────────────────────▶│                    │                       │                    │
     │                          │  /api/*            │                       │                    │
     │                          │───────────────────▶│                       │                    │
     │                          │                    │  http :8001           │                    │
     │                          │                    │  /api/...             │                    │
     │                          │                    │──────────────────────▶│                    │
     │                          │                    │                       │                    │
     │                          │                    │                       │  1. RateLimitMW    │
     │                          │                    │                       │     60 req/min/key │
     │                          │                    │                       │                    │
     │                          │                    │                       │  2. RequestSizeMW  │
     │                          │                    │                       │     ≤ 1 MiB body   │
     │                          │                    │                       │                    │
     │                          │                    │                       │  3. verify_bearer │
     │                          │                    │                       │     hmac.compare   │
     │                          │                    │                       │                    │
     │                          │                    │                       │  4. Pydantic valid │
     │                          │                    │                       │     max_length OK  │
     │                          │                    │                       │                    │
     │                          │                    │                       │  5. Business logic │
     │                          │                    │                       │     (e.g. CRUD)    │
     │                          │                    │                       │                    │
     │                          │                    │                       │  6. write          │
     │                          │                    │                       │───────────────────▶│
     │                          │                    │                       │                    │
     │                          │                    │                       │  7. ack            │
     │                          │                    │                       │◀───────────────────│
     │                          │                    │                       │                    │
     │                          │                    │  8. JSON response     │                    │
     │                          │                    │◀──────────────────────│                    │
     │                          │  9. HTTPS response │                       │                    │
     │                          │◀───────────────────│                       │                    │
     │  10. render              │                    │                       │                    │
     │◀─────────────────────────│                    │                       │                    │
     │                          │                    │                       │                    │
```

If any of steps 1–4 fail, the response is generated **before** the
business logic runs, so a denied request never touches Mongo.

---

## 3. Chat / RAG pipeline

What happens when the user asks Little Dove a question that needs their
own documents.

```
 User            Frontend           Backend (FastAPI)        Ollama (local)         MongoDB
 ────            ────────           ─────────────────        ──────────────         ───────
   │                 │                      │                      │                   │
   │  "What does     │                      │                      │                   │
   │   our SLA say?" │                      │                      │                   │
   │────────────────▶│                      │                      │                   │
   │                 │  POST /api/rag/query │                      │                   │
   │                 │  Bearer <CB_API_KEY> │                      │                   │
   │                 │─────────────────────▶│                      │                   │
   │                 │                      │                      │                   │
   │                 │                      │ 1. embed(query)      │                   │
   │                 │                      │   deterministic      │                   │
   │                 │                      │   32-dim vector      │                   │
   │                 │                      │                      │                   │
   │                 │                      │ 2. cosine top-K      │                   │
   │                 │                      │   against            │                   │
   │                 │                      │   rag_embeddings     │                   │
   │                 │                      │───────────────────────────────────────▶   │
   │                 │                      │                      │                   │
   │                 │                      │   top-K chunks ◀─────────────────────────│
   │                 │                      │                      │                   │
   │                 │                      │ 3. build prompt      │                   │
   │                 │                      │   context = chunks   │                   │
   │                 │                      │   "If context lacks  │                   │
   │                 │                      │    the answer, say   │                   │
   │                 │                      │    so."              │                   │
   │                 │                      │                      │                   │
   │                 │                      │ 4. POST /api/generate│                   │
   │                 │                      │  { model, prompt,    │                   │
   │                 │                      │    stream: false }   │                   │
   │                 │                      │─────────────────────▶│                   │
   │                 │                      │                      │                   │
   │                 │                      │   answer text        │                   │
   │                 │                      │◀─────────────────────│                   │
   │                 │                      │                      │                   │
   │                 │                      │ 5. log exchange      │                   │
   │                 │                      │   (no persistence    │                   │
   │                 │                      │    of model output   │                   │
   │                 │                      │    across requests)  │                   │
   │                 │                      │                      │                   │
   │                 │  JSON { answer,      │                      │                   │
   │                 │         sources }    │                      │                   │
   │                 │◀─────────────────────│                      │                   │
   │                 │                      │                      │                   │
   │  render answer  │                      │                      │                   │
   │◀────────────────│                      │                      │                   │
   │                 │                      │                      │                   │
```

Notes:

- Embedding is deterministic and in-process — **no** external embedding
  service is required.
- The RAG prompt explicitly tells the model that context is **data, not
  instruction** (mitigation for T5 — prompt injection).
- Chat history is **not** persisted across requests. A successful
  injection only affects the operator's own deployment.

---

## 4. Audit pipeline

What happens when the operator clicks **Run audit** in Commander.

```
 Operator       Frontend         Backend (FastAPI)         Commander            PDF
 ────────       ────────         ─────────────────         ─────────            ───
    │              │                    │                      │                  │
    │  click       │                    │                      │                  │
    │  "Run audit" │                    │                      │                  │
    │─────────────▶│                    │                      │                  │
    │              │  POST /api/audit/  │                      │                  │
    │              │  run               │                      │                  │
    │              │  Bearer <key>      │                      │                  │
    │              │───────────────────▶│                      │                  │
    │              │                    │                      │                  │
    │              │                    │ 1. BoundedSemaphore  │                  │
    │              │                    │    (cap = 2)         │                  │
    │              │                    │                      │                  │
    │              │                    │ 2. spawn subprocess  │                  │
    │              │                    │  ┌──────────────────┐│                  │
    │              │                    │  │  verify_all.py   ││                  │
    │              │                    │  │  - unit tests    ││                  │
    │              │                    │  │  - validators    ││                  │
    │              │                    │  │  - fuzz checks   ││                  │
    │              │                    │  │  - conformance   ││                  │
    │              │                    │  └────────┬─────────┘│                  │
    │              │                    │           │         │                  │
    │              │                    │           │  stdout │                  │
    │              │                    │           │  JSON   │                  │
    │              │                    │           ▼         │                  │
    │              │                    │                      │                  │
    │              │                    │ 3. append audit row  │                  │
    │              │                    │  hash-linked log ───▶│                  │
    │              │                    │  prev_hash = tail    │                  │
    │              │                    │                      │                  │
    │              │                    │ 4. compute SHA-256   │                  │
    │              │                    │    over body         │                  │
    │              │                    │                      │                  │
    │              │                    │ 5. Ed25519 sign      │                  │
    │              │                    │    with local key    │                  │
    │              │                    │                      │                  │
    │              │                    │ 6. render PDF ────────────────────────▶ │
    │              │                    │    letterhead                          (file)
    │              │                    │    entity #14694374-0160               (file)
    │              │                    │    SHA-256 attestation
    │              │                    │    signature block
    │              │                    │                      │                  │
    │              │  JSON { audit_id,  │                      │                  │
    │              │    sha256,         │                      │                  │
    │              │    pdf_url }       │                      │                  │
    │              │◀───────────────────│                      │                  │
    │              │                    │                      │                  │
    │  "Download   │                    │                      │                  │
    │   signed PDF"│                    │                      │                  │
    │─────────────▶│                    │                      │                  │
    │              │  GET /api/audit/   │                      │                  │
    │              │  <id>/pdf          │                      │                  │
    │              │───────────────────▶│                      │                  │
    │              │                    │  stream PDF ◀────────────────────────  │
    │              │◀───────────────────│                      │                  │
    │  save file   │                    │                      │                  │
    │◀─────────────│                    │                      │                  │
    │              │                    │                      │                  │
```

Anyone holding `release/signing-public-key.pem` can verify the PDF
signature and the SHA-256 body hash — no out-of-band trust required.

---

## 5. Deploy paths

All four converge on the same backend image and the same env-var contract.

```
                        ┌────────────────────────────────────────┐
                        │  ThirstyAi Builder — same backend,     │
                        │  same env-var contract, same preflight │
                        └─────────────────┬──────────────────────┘
                                          │
        ┌───────────────────┬─────────────┼─────────────┬────────────────────┐
        │                   │             │             │                    │
        ▼                   ▼             ▼             ▼                    ▼
 ┌─────────────┐    ┌──────────────┐  ┌────────┐  ┌──────────┐    ┌────────────────┐
 │  Railway    │    │ Vercel+Render│  │  Fly   │  │   VPS    │    │  iPhone (any)  │
 │  ~$5/mo     │    │  free tier   │  │  $0-5  │  │  $5-40   │    │  mobile deploy │
 │  ~4 min     │    │  ~10 min     │  │  ~5min │  │  ~30 min │    │  via GH app    │
 │             │    │              │  │        │  │          │    │                │
 │ compose-    │    │ Vercel: SPA  │  │ fly    │  │ Docker + │    │ git push →     │
 │ detects     │    │ Render: ctr  │  │ launch │  │ Compose  │    │ import to      │
 │ 3 services  │    │ Atlas: Mongo │  │ secrets│  │ + Ollama │    │ Railway/Vercel │
 └──────┬──────┘    └──────┬───────┘  └───┬────┘  └────┬─────┘    └───────┬────────┘
        │                 │              │            │                  │
        └─────────────────┴──────────────┴────────────┴──────────────────┘
                                          │
                                          ▼
                       ┌────────────────────────────────┐
                       │  Reverse proxy (TLS term)      │
                       │  Caddy or nginx + HSTS         │
                       │  public entrypoint             │
                       └────────────────┬───────────────┘
                                        ▼
                       ┌────────────────────────────────┐
                       │  Backend (FastAPI :8001)       │
                       │  + Mongo + remote Ollama       │
                       │  reachable over Tailscale /    │
                       │  WireGuard / SSH tunnel        │
                       └────────────────────────────────┘
```

The "remote Ollama" can be the same host (loopback) or a different host
over a private tunnel. See `HOSTED_OLLAMA.md` for the tunnel recipes.

---

## 6. Trust boundaries

The four boundaries from `THREAT_MODEL.md`, drawn explicitly.

```
 Boundary 1 (browser ↔ reverse proxy)
 ─────────────────────────────────────
 [Browser]  ──HTTPS, HSTS, single-origin──▶  [Reverse proxy :443]
   • TLS 1.2+
   • HSTS on
   • CSP forbids cross-origin script/frame loads


 Boundary 2 (frontend nginx ↔ backend)
 ──────────────────────────────────────
 [Frontend nginx :3000]  ──same compose net──▶  [Backend :8001]
   • Bearer token on every non-public route
   • 60 req/min/key rate limit
   • 1 MiB body size cap
   • Pydantic max_length on every free-text field


 Boundary 3 (backend ↔ MongoDB)
 ──────────────────────────────
 [Backend]  ──internal network──▶  [MongoDB in container]
   • Mongo binds to loopback in its container
   • No host port mapping (27017 not on the public internet)
   • In production: THIRSTY_AI_REQUIRE_MONGO=1 → fail-closed


 Boundary 4 (backend ↔ Ollama)
 ────────────────────────────
 [Backend]  ──Tailscale / WireGuard / SSH──▶  [Ollama on a host]
   • Ollama binds to 127.0.0.1 only (NEVER 0.0.0.0)
   • The tunnel maps the backend's loopback to Ollama's loopback
   • Ollama API has no auth — the network path is the only thing
     protecting it. Tunneled, not public.
```

The hard rules:

1. **Ollama binds to 127.0.0.1 only.** Never 0.0.0.0.
2. **MongoDB has no host port mapping.** Loopback inside the container
   is enough; the compose network reaches it.
3. **The backend's host port (8001) is not published to the public
   internet.** The frontend nginx is the only public entrypoint.
4. **TLS terminates at the reverse proxy.** The backend speaks plain
   HTTP inside the trust boundary.

---

## 7. Release artifact

Every release produces the same four artifacts under `release/`.

```
  source/   →   release/sbom.json   →   release/package-manifest.json
    │                │                          │
    │                ▼                          ▼
    │         CycloneDX SBOM          ZIP package of source
    │         lists every direct      + SBOM + manifest
    │         dep and its version     + signing public key
    │                │                          │
    │                │                          ▼
    │                │              release/constitutional-builder-<ver>.zip
    │                │                          │
    │                │                          ▼
    │                │              release/provenance.json
    │                │              (who built what, when, with what)
    │                │                          │
    │                │                          ▼
    │                │              release/provenance.signature.json
    │                │              (Ed25519 signature over provenance)
    │                │                          │
    │                │                          ▼
    │                │              release/package-signature.json
    │                │              (Ed25519 signature over the ZIP)
    │                │                          │
    │                └──────────────────────────┘
    │                                │
    │                                ▼
    │              release/signing-public-key.pem
    │              (the public half of the Ed25519 keypair;
    │               private key never enters the repo)
    ▼
  Source of truth: the local checkout, pinned by commit hash.
```

Verification (for a recipient):

```bash
# 1. Confirm the ZIP matches the manifest
sha256sum -c release/provenance.json

# 2. Confirm the Ed25519 signature matches
python -c "
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError
vk = VerifyKey(open('release/signing-public-key.pem','rb').read())
try:
    vk.verify(open('release/constitutional-builder-0.1.0.zip','rb').read(),
              open('release/package-signature.json','rb').read())
    print('OK: signature valid')
except BadSignatureError:
    print('FAIL: signature invalid')
"

# 3. Re-build from the SBOM and compare hashes
python scripts/build_release_package.py --check
```
