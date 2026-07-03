# Changelog

All notable changes to the ThirstyAi Builder are recorded here. Dates
are in `YYYY-MM-DD` (UTC). Versions follow [SemVer](https://semver.org/).

## [Unreleased] — Documentation refresh

### Added
- `README.md` — full rewrite. Opens with a **30-second pitch** split
  into three audiences (non-engineer, engineer, 60-second visual).
  Followed by a table of contents, repository map, **lists** of the 11
  UI pages and the 7 App Store tools, **features** for non-engineers
  and engineers, a **diagrams** pointer to `docs/DIAGRAMS.md`,
  installation methods (with a pointer to `docs/INSTALL.md`),
  configuration reference, daily operations, deploy summary, security
  pointers, ownership block, doc index, and an FAQ.
- `docs/DIAGRAMS.md` — single source of visual truth. Seven diagrams
  in ASCII: system topology, request flow end-to-end, chat / RAG
  pipeline, audit pipeline, deploy paths, trust boundaries, release
  artifact. No external tooling; renders in any monospaced font.
- `docs/INSTALL.md` — full install matrix: three tracks (local dev,
  Docker Compose, production) × three operating systems (Windows,
  macOS, Linux). Plus Ollama install for every OS, first-run checks
  (health, preflight, auth, footer, chat), and uninstall / reset.
- `INSTALL.md` — thin alias at the repo root pointing at
  `docs/INSTALL.md`, so the README's "Installation Methods" link works
  from the repo root and from inside the package.

### Changed
- `README.md` — was a quickstart cheat sheet; is now a structured
  entry point. The quickstart itself moved to `docs/INSTALL.md` §1–§3.
- `OWNER_HANDOFF.md` — unchanged. Already references the README.

### Not changed
- `DEPLOY.md`, `SECURITY.md`, `THREAT_MODEL.md`, `HOSTED_OLLAMA.md`,
  `OWNERSHIP.md` — these stay as the deep-dive docs that the new
  README points into.
- Code, tests, release artifact — no functional changes. The SBOM,
  package, and Ed25519 signature under `release/` remain valid for
  the prior commit; this release is a docs-only update.

---

## [1.0.0] — Self-hosted production deployment gates

**Commit:** `fecfdf6` (HEAD at time of this entry)

### Added
- Production preflight: `python -m thirsty_ai_builder_backend.preflight`
  refuses to pass if `CB_API_KEY` is missing or weak, if Mongo is
  unreachable, or if required env vars are absent.
- `THIRSTY_AI_REQUIRE_AUTH=1` — fail-closed at backend startup if
  `CB_API_KEY` is missing.
- `THIRSTY_AI_REQUIRE_MONGO=1` — fail-closed at backend startup if
  Mongo is missing or unreachable.
- `THIRSTY_AI_TRUST_PROXY` — opt-in trust of `X-Forwarded-For` from
  a known reverse proxy.
- `release/` — CycloneDX SBOM, package manifest, Ed25519 signature,
  hardened systemd unit (`deploy/ollama.service`), Caddy and nginx
  configs for TLS termination, Tailscale / WireGuard / SSH recipes
  for hosted Ollama.
- `HOSTED_OLLAMA.md` — full operator runbook for hosting Ollama on
  a separate host.
- `THREAT_MODEL.md` — assets, adversaries, four trust boundaries,
  and the top ten threats (T1–T10) with mitigations.
- `SECURITY.md` — supported versions, reporting channel, 72-hour
  acknowledgement, 90-day disclosure window, 12-item hardening
  checklist.
- Rust CI auditor (`rust-auditor/`) with a drop-in GitHub Actions
  workflow.

### Changed
- `RequestSizeLimitMiddleware` — caps every body at 1 MiB
  (configurable via `THIRSTY_AI_MAX_REQUEST_BYTES`).
- `RateLimitMiddleware` — 60 req/min/key.
- Pydantic models — `max_length` on every free-text field.
- The `verify_all.py` gate now includes deployment validation,
  release-evidence generation, package build, and signature checks.

---

## Earlier history

The full commit log lives in `git log`. The Commander audit log lives
in `commander/audit-log.md` (at the repository root) and the final
certification report lives in `commander/final-certification-report.md`.
