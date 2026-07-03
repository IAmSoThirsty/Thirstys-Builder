# Security Policy

## Supported versions

The ThirstyAi Builder tracks `main`. Security fixes are backported to the most recent release. There is no LTS release; this is a single-tenant local / self-hosted app, not a multi-tenant SaaS.

| Branch | Supported |
|---|---|
| `main` | Yes |
| older commits | No |

## Reporting a vulnerability

**Email:** founderoftp@thirstysprojects.com
**Subject prefix:** `[security]`

Please include:

1. A description of the vulnerability and its impact.
2. Reproduction steps (a curl command, a request payload, or a short script is ideal).
3. The commit hash or release tag you reproduced against.
4. Your assessment of severity (Critical / High / Medium / Low) and a one-line justification.

You will receive an acknowledgement within 72 hours. I will follow up with a triage decision and a fix timeline within 7 days for Critical and High severity issues.

## What to expect

- **Acknowledgement:** within 72 hours.
- **Triage:** within 7 days for Critical / High. Lower severity issues are batched.
- **Fix:** the fix lands on `main`, is covered by a test, and is mentioned in the audit log (`commander/audit-log.md`).
- **Credit:** if you would like to be credited in the fix commit and the audit log, say so in the report. Otherwise the fix is anonymous.
- **Disclosure:** I follow a 90-day disclosure window. If the fix lands sooner, the advisory is published when the fix ships. If the fix needs more time, I will coordinate a disclosure date with you.

## What NOT to file here

- **General support questions.** Use the contact in `OWNER_HANDOFF.md` §9.
- **Bug reports that are not security issues.** Those go in the issue tracker, not the security channel.
- **Dependency CVEs that you have not verified.** A `pip-audit` finding that I cannot reproduce is not a vulnerability report. Verify it against a checkout of this repo, include the exact dep version and the `pip-audit` output, and reference the CVE.

## Hardening checklist for self-hosted deployments

This is what I do on every deployment I run. A reviewer should be able to confirm each item.

- [ ] `CB_API_KEY` set to a fresh 32-byte URL-safe random string, stored in a secret manager, not in the repo or `.env` file in version control.
- [ ] `THIRSTY_AI_REQUIRE_AUTH=1` set for production/self-hosted deployments so startup fails closed if `CB_API_KEY` is missing.
- [ ] `MONGO_URL` set to a real Mongo instance, NOT the in-memory stub.
- [ ] `THIRSTY_AI_REQUIRE_MONGO=1` set for production/self-hosted deployments so startup fails closed if Mongo is missing or unreachable.
- [ ] `python -m thirsty_ai_builder_backend.preflight` passes before the service is exposed.
- [ ] `OLLAMA_HOST` points at a tunneled Ollama host. Ollama binds to 127.0.0.1, not 0.0.0.0. See `HOSTED_OLLAMA.md`.
- [ ] TLS terminated at a reverse proxy (Caddy or nginx) with the supplied `deploy/Caddyfile` or `deploy/nginx.conf`. HSTS is on, modern TLS only.
- [ ] The backend's host port (`8001`) is NOT exposed to the public internet. The frontend nginx (port `3000`) is the only public entrypoint. The frontend proxies `/api/*` to the backend on the same origin.
- [ ] The MongoDB port (`27017`) is NOT exposed to the public internet. Docker Compose has no `ports:` mapping for the `mongo` service.
- [ ] Backups: Mongo data is backed up nightly. Ollama models are re-pullable, so they do not need backup.
- [ ] Updates: `pip-audit` and `npm audit` are run weekly; CVEs are patched within 14 days of disclosure.
- [ ] Logs: backend logs are shipped to a central log store; auth failures and rate-limit hits are alerted on.
- [ ] `THIRSTY_AI_TRUST_PROXY=1` is set ONLY when behind a trusted reverse proxy. Setting it elsewhere lets clients spoof their IP.

## Cryptography

- **Release signing:** Ed25519 via `cryptography` (PyCA). Public key at `release/signing-public-key.pem`. Private key is generated locally and never enters the repo.
- **Auth tokens:** opaque random strings (32 bytes), not JWTs. `hmac.compare_digest` for verification.
- **TLS:** terminated at the reverse proxy. The backend itself speaks plain HTTP inside the trust boundary.
- **Password storage:** N/A. The app does not store user passwords.
- **At-rest encryption:** depends on the operator's MongoDB deployment. The compose file does not enable disk encryption; use the cloud provider's encrypted volume option, or `cryptsetup` on a VPS.

## Past advisories

None published yet. The repo is on its first stable release.

## Acknowledgements

None yet.
