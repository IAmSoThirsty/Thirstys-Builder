# Threat Model

**Scope:** the ThirstyAI Builder backend (FastAPI in `thirsty-ai-builder/backend/`), the React frontend, the MongoDB persistence layer, and the local Ollama LLM service. The Constitutional Builder (CBEP) at the repo root is a separate kernel; its threat model lives in `spec/volume-07-security-architecture.md`.

**Out of scope:** the operator's host OS, the cloud account that hosts the deployment, the Ollama model files themselves, and any third-party services the operator wires in (e.g. a managed MongoDB). Those have their own threat models and the operator owns them.

---

## 1. Assets

| Asset | Where it lives | Sensitivity |
|---|---|---|
| `CB_API_KEY` | Operator's `.env` / secret manager | High. Bearer token for every authenticated route. |
| MongoDB connection string | Operator's `.env` | Medium. Holds audit PDFs, business clients, RAG embeddings. |
| Audit PDFs (signed) | MongoDB `audits` collection | High. Documented client deliverables. |
| RAG embeddings | MongoDB `rag_embeddings` collection | Low–Medium. Vector text snippets the operator chose to embed. |
| Business clients (names, emails) | MongoDB `clients` collection | Medium. PII if the operator collects it. |
| Ollama chat history | Memory only (not persisted) | Low. |
| Source code | Repo | Low (proprietary license protects the IP). |
| Ownership block | Repo (compile-time) | Low. Public by design. |

The Ed25519 signing key for release artifacts is generated locally per machine. The private key never enters the repo; the public key is at `release/signing-public-key.pem`.

## 2. Adversaries

1. **Internet attacker (unauthenticated).** Can hit `/api/health`, `/api/ownership`, `/`, `/docs`, `/openapi.json`. Cannot reach authenticated endpoints without `CB_API_KEY`. The threat model assumes the deployment is on a publicly-reachable host (Railway, Vercel+Render, Fly, VPS) with a TLS-terminating reverse proxy in front.

2. **Authenticated client (low privilege).** Has `CB_API_KEY`. Can hit every endpoint. Treated as a legitimate user who may try to break the system through normal API use (oversized payloads, path traversal, prompt injection).

3. **Authenticated client (abusive).** Has `CB_API_KEY` and tries to abuse — flooding chat endpoints to make the operator's GPU bill spike, scraping the audit list, exfiltrating business data, etc.

4. **Network adversary on the local network.** Can sniff traffic between the frontend and backend. Mitigated by TLS at the reverse proxy; the app does not assume a trusted network.

5. **Compromised Ollama host.** A separate machine that runs `ollama serve`. The Ollama API has no authentication, so any process that can reach the port can read or generate text. Mitigated by binding Ollama to 127.0.0.1 and tunneling over Tailscale / WireGuard / SSH (see `HOSTED_OLLAMA.md`).

6. **Malicious model output.** The local LLM can be prompted to produce text the operator does not want (prompt injection, harmful content, leakage of other users' data). Mitigated by: no persistence of model output across requests, no automatic execution of model output, and the operator choosing the model.

7. **Insider with repo access.** Can read the source, including the ownership block and the proprietary license. Cannot read the operator's secrets unless they are in the repo (the deployment scripts explicitly forbid that).

## 3. Trust boundaries

```
[ Browser ]
    | (HTTPS, same-origin)
[ Reverse proxy ]   <- terminates TLS, adds HSTS
    |
[ Frontend (nginx) ]   <- serves static SPA + proxies /api
    |
[ Backend (FastAPI) ]   <- auth, validation, business logic
    |
    +-- [ MongoDB ]   <- persistence
    |
    +-- [ Ollama ]   <- LLM (over Tailscale / WireGuard / loopback)
```

- **Boundary 1: browser ↔ reverse proxy.** TLS. HSTS. Single-origin. CSP forbids cross-origin script and frame loads.
- **Boundary 2: frontend nginx ↔ backend.** Same compose network. Bearer token required on every non-public endpoint.
- **Boundary 3: backend ↔ MongoDB.** Internal network. Mongo binds to the loopback interface inside its container; no host port mapping.
- **Boundary 4: backend ↔ Ollama.** Tunneled. Ollama binds to 127.0.0.1; the tunnel maps the backend's loopback port to Ollama's loopback port. No auth, but the network path is private.

## 4. Top threats and mitigations

### T1. CORS misconfiguration

**Threat:** A developer sets `CORS_ORIGINS=*` with credentials and the browser sends authenticated requests to attacker-controlled origins.

**Mitigation:** the backend refuses the `*` + credentials combination. If `*` is set, credentials are forced off. The default is `http://localhost:3000`. The single-origin frontend (nginx proxies `/api` to the backend) means production deployments do not need cross-origin at all.

**Residual risk:** if an operator explicitly sets `CORS_ORIGINS=https://attacker.example`, the backend will honor it. The README and DEPLOY.md warn against this.

### T2. Unbounded request body → OOM

**Threat:** A 100MB POST to `/api/rag/embed` is buffered by the app, eating memory.

**Mitigation:** `RequestSizeLimitMiddleware` rejects bodies larger than 1 MiB (configurable via `THIRSTY_AI_MAX_REQUEST_BYTES`). Pydantic field caps are a second line of defense: `RAGEmbedRequest.text` is capped at 16,000 characters, `ChatRequest.message` at 8,000, etc.

### T3. Brute force on `CB_API_KEY`

**Threat:** Attacker tries every possible token.

**Mitigation:** the token is a 32-byte URL-safe random string (`secrets.token_urlsafe(32)`), giving 256 bits of entropy. `verify_bearer` uses `hmac.compare_digest` to avoid timing attacks. `RateLimitMiddleware` throttles unauthenticated requests to 60/min/key, and the auth dependency returns 503 when no token is configured (so the attack surface is reduced before any guessing).

Production/self-hosted deployments set `THIRSTY_AI_REQUIRE_AUTH=1`, so backend startup fails closed unless `CB_API_KEY` is configured. Operators also run `python -m thirsty_ai_builder_backend.preflight`, which rejects missing, short, or placeholder-looking tokens before exposure.

### T4. DoS via the LLM

**Threat:** A flood of chat requests makes the operator's GPU bill spike.

**Mitigation:** `RateLimitMiddleware` throttles to 60 req/min/key (configurable). The audit endpoint has a `BoundedSemaphore(2)` so a flood cannot fork an unbounded number of 600-second subprocesses. The Ollama host is operator-controlled; if the operator sees a spike, they can kill Ollama or block the tunnel.

### T5. Prompt injection in RAG

**Threat:** An operator embeds untrusted text (e.g. a customer document) and the LLM uses it as instruction. A user then queries and the LLM follows the injected instruction instead of answering the question.

**Mitigation:** RAG context is treated as data, not as instruction. The prompt explicitly says "If the context does not contain the answer, say so." Operators are warned in the runbook to review what they embed. The model is local, so a successful injection only affects the operator's own deployment.

**Residual risk:** real mitigation requires a model trained to distinguish context from instruction. The current design relies on the operator choosing the model.

### T6. Audit PDF forgery

**Threat:** An attacker with DB write access replaces a real audit with a forged one.

**Mitigation:** every audit is signed by the local Ed25519 key. The signed PDF includes the entity number, the audit ID, and a SHA-256 of the body. The recipient can verify the signature against `release/signing-public-key.pem` (shipped with the repo). DB write access requires `CB_API_KEY`.

**Residual risk:** the signing key is local. A compromised host compromises the signature. KMS / HSM-based signing is Stage 3 work.

### T7. Information disclosure via error messages

**Threat:** A stack trace or DB error string leaks an internal path, schema, or dependency version.

**Mitigation:** `/api/health/ready` no longer echoes the raw exception text — it logs the detail and returns the opaque string `unavailable`. FastAPI's default exception handler returns a generic 500 for unhandled exceptions. Pydantic validation errors return field-level errors (which is necessary for client UX) but no internal paths.

### T8. Mongo as the silent-fallback foot-gun

**Threat:** Operator deploys without setting `MONGO_URL` and the app silently uses the in-memory stub. Production data is lost on restart.

**Mitigation:** production/self-hosted deployments set `THIRSTY_AI_REQUIRE_MONGO=1`. In that mode, backend startup fails closed unless `MONGO_URL` is set and the server responds to `ping`. The in-memory backend remains available only for local development and tests.

The production preflight also rejects missing or malformed `MONGO_URL` before the service is exposed.

### T9. Dependency vulnerabilities

**Threat:** A transitive dep has a CVE that the repo's tests do not catch.

**Mitigation:** all backend deps are pinned with upper bounds in `requirements.txt` (`fastapi>=0.110,<1` etc). `release/sbom.json` is a CycloneDX SBOM that lists every direct dep and its version. The release artifact is reproducible from the SBOM.

**Residual risk:** a CVE lands between releases. Operators are expected to monitor the Python advisory database and bump when needed. An automated `pip-audit` step in CI is planned.

### T10. Container breakout

**Threat:** A vulnerability in FastAPI, Uvicorn, or Python allows code execution inside the backend container, which then breaks out to the host.

**Mitigation:** the backend container runs as a non-root UID (10001), with `no-new-privileges`, `read_only: true` (with a small tmpfs for `/tmp`), and all Linux capabilities dropped except `NET_BIND_SERVICE`. The Mongo container runs as UID 999 with `no-new-privileges`. The frontend container drops all capabilities except the minimum nginx needs.

## 5. What this threat model does NOT cover

- **Physical security** of the host. Operator's responsibility.
- **Cloud account security** (IAM, network ACLs). Operator's responsibility.
- **Ollama model safety** (bias, hallucination, harmful content). Operator's responsibility when picking a model.
- **Supply chain attacks** via npm or PyPI. Mitigated by pinning versions and a reproducible build, but a compromised upstream is not detectable from the repo alone.
- **Side-channel attacks** on the LLM inference (timing, GPU memory). Out of scope for a single-tenant local deployment.
- **Quantum-safe crypto** for the Ed25519 signatures. Ed25519 is the industry standard; post-quantum migration is a separate concern.

## 6. Review checklist

A reviewer should be able to answer YES to each:

- [ ] No secrets in the repo (`git grep -i 'api[_-]\?key\|password\|secret\|token='` returns only documentation references, no values).
- [ ] `requirements.txt` has version pins (lower and upper bounds) for every dep.
- [ ] The SBOM in `release/sbom.json` lists every dep.
- [ ] The Dockerfile runs as a non-root user.
- [ ] The Docker Compose file drops capabilities and sets `no-new-privileges`.
- [ ] The auth dependency uses constant-time token comparison.
- [ ] Production deployment sets `THIRSTY_AI_REQUIRE_AUTH=1`, and startup fails if `CB_API_KEY` is missing.
- [ ] Production deployment sets `THIRSTY_AI_REQUIRE_MONGO=1`, and startup fails if Mongo is missing or unreachable.
- [ ] `python -m thirsty_ai_builder_backend.preflight` passes before exposure.
- [ ] The chat endpoint returns 503 when Ollama is unreachable, not 500.
- [ ] The health endpoint does not leak exception text.
- [ ] Pydantic models have `max_length` on every free-text field.
- [ ] The `RequestSizeLimitMiddleware` is registered before the route handlers.
- [ ] The Ollama API binds to 127.0.0.1, not 0.0.0.0.
- [ ] `verify_all.py` is green.
