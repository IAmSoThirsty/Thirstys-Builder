# Changelog

All notable changes to the ThirstyAI Builder are recorded here. Dates
are in `YYYY-MM-DD` (UTC). Versions follow [SemVer](https://semver.org/).

## [v0.4.0-prep] — 2026-07-04 — Personal Builder Coder Modelfile (in-repo)

### Added
- **Personal Builder Coder Modelfile moved into the repo.**
  The `personal-builder-coder` Ollama model was previously a hand-curated
  Modelfile living in Ollama's blob store with a system-prompt
  generated on 2026-07-02. v0.4.0-prep pins it to `git` and signs it
  with the project's existing Ed25519 release key, so the model is
  reproducible from `git clone + python scripts/build_personal_builder_coder.py`.
- **`models/personal-builder-coder/Modelfile`** — verbatim
  `ollama show personal-builder-coder:latest --modelfile` output:
  FROM line, Qwen 2.5 chat template with FIM and tool-calling,
  full system prompt (core operating contract + 14 trained
  principles), `PARAMETER num_ctx 8192`, `PARAMETER temperature 0.2`.
- **`models/personal-builder-coder/source-evidence.json`** — 22 source
  papers cited by the Modelfile's principle layer, each with path,
  size, and a real full SHA-256 (not the truncated 16-char prefix
  from the Modelfile). Manifest includes 8 papers the Modelfile's
  source list did not cite (AADA, Operational Destruction Review,
  Constitutional Code Store, Project-AI In-Drive, AEGIS, The Vision,
  Sovereign Monolith, Sovereign Covenant) so the principle layer
  has room to grow without losing integrity.
- **`models/personal-builder-coder/manifest.json`** — schema with
  name, version, base model (`qwen2.5-coder:7b`), upstream digest
  (`60e05f2100071479f596b964f89f510f057ce397ea22f2833a0cfe029bfc2463`),
  architecture (qwen2, 7.6B, Q4_K_M), parameters, capabilities,
  Modelfile sha, source-evidence sha. Honest about being a
  Modelfile, not a fine-tune.
- **`models/personal-builder-coder/manifest.signature.json`** —
  Ed25519 signature over the canonical-JSON form of manifest.json,
  using the same `TEST_SEED` as `release/package-signature.json`.
  Verifies against `release/signing-public-key.pem`. Key fingerprint
  `30934b906a55ee6d` (matches).
- **`scripts/build_personal_builder_coder.py`** — three modes:
  - default: verifies manifest + signature, then runs
    `ollama create personal-builder-coder:v0.4.0-prep -f Modelfile`
  - `--check`: manifest + signature only (no Ollama call)
  - `--remove`: tears down the tag
- **`tests/test_personal_builder_coder_manifest.py`** — 14 tests:
  files exist, Modelfile sha matches, source-evidence sha matches,
  signature verifies against release public key, signature key
  fingerprint matches the PEM, schema has required keys, base
  metadata correct, parameters correct, kind string honest about
  no-finetune, all 22 papers exist on disk with matching SHA-256,
  slugs unique, filenames unique.

### Security
- Manifest signed with the same Ed25519 key as the existing release
  package. The signature is over the canonical-JSON form, which
  means any whitespace or key-order change to manifest.json
  invalidates the signature. Tampering with the Modelfile,
  source-evidence, or upstream digest all break the chain.
- The source-evidence SHA-256s are computed at build time and
  verified at test time. A paper that gets moved or edited
  without updating the manifest fails `pytest`.
- `kind: modelfile-on-upstream-weights` and a `note` field that
  says "It is not a fine-tuned model" so anyone reading the
  manifest in a year knows what this artifact is.

### Changed
- `scripts/verify_all.py` — added step 13b: `build_personal_builder_coder.py --check`.
  Runs on every gate, fails the gate if the manifest is stale,
  tampered, or missing papers.

### Not in v0.4.0-prep (deferred)
- **Fine-tuning.** The hardware probe (Windows + AMD Radeon iGPU
  with 0.5 GB VRAM, no CUDA) means QLoRA on Qwen 2.5 Coder 1.5B/7B
  is not realistic on this machine. Future work: rent an A100/4090
  for ~$5-10, or wait for better local hardware. The Modelfile
  is the model for now; the manifest makes that explicit.
- **Drift enforcement in the federation protocol.** Queued for v0.3.1
  (federation work), not the model work.

---

## [v0.3.0] — 2026-07-04 — Live multi-host consensus (federation)

### Added
- **Live federation** at `source/constitutional_builder/federation/`.
  Real HTTP between 3+ node processes on loopback, with the same
  quorum math as the in-process `QuorumCluster` but exercised over
  a real wire. Closes the 0.2.0 roadmap line: "Multi-host consensus
  (CBEP volume 8) - actual federation, not just the conformance check."
- **Wire protocol** (`federation/protocol.py`): `FederationMessage`
  with `ASK`, `HEARTBEAT`, `POLICY_DIGEST_MISMATCH` kinds. CBEP-003
  attestation envelope. `VoteBody` and `HeartbeatBody` payload types.
  `policy_digest` for drift detection.
- **HTTP transport** (`federation/transport.py`): standard-library
  `ThreadingHTTPServer`, JSON only, no new dependencies. Bearer
  token = SHA-256(public_key)[:16] hex. Loopback-only by default
  (constructor refuses to bind to non-loopback hosts).
- **`LiveCluster`** (`federation/cluster_live.py`): N real HTTP
  nodes, peer topology, partition mask for tests, preserves
  liveness state across partition changes.
- **Split-brain guard**: the quorum bar is the *configured* cluster
  size, not the visible size. A node that can see fewer than
  quorum-many peers denies the request with reason
  "cluster partition - quorum unreachable". Same property Raft and
  Paxos enforce, no leader required.
- **Drift detection hook**: `policy_digest` is computed from the
  node's `PolicyEngine` rules and sent in every heartbeat. The
  enforcement path (refusing a drift peer's vote) is reserved for
  v0.3.1 — the digest is on the wire today.
- **`ActionRequest.to_dict` / `from_dict`**: wire-friendly
  roundtrip on the model. Same shape on the wire as in
  `policy_bundle.json` for portability.
- **15 new tests** in `tests/test_live_federation.py`: baseline,
  single-peer partition, two-peer split-brain, recovery,
  configured-vs-visible quorum, hash determinism, message
  roundtrip, version mismatch rejection, fingerprint stability,
  policy-digest drift detection, vote body roundtrip, server
  loopback enforcement, info endpoint.
- **`scripts/run_live_federation_conformance.py`**: 6-step
  end-to-end conformance used by the CBEP gate. Step 16 of
  `scripts/verify_all.py`.
- **`docs/FEDERATION.md`**: full reference for the protocol,
  the wire format, the test matrix, the multi-host deployment
  instructions (WireGuard / Tailscale), and the open work.

### Security
- Server refuses to bind to non-loopback addresses. Multi-host
  requires either a non-loopback whitelist (open work) or
  fronting the server with a reverse proxy. Documented.
- Bearer token is the SHA-256 of the public key (first 16 hex
  chars). 64 bits of identity, no key material on the wire.
- Drift detection is in place; enforcement is queued.

### Changed
- `ActionRequest` gained `to_dict` / `from_dict` for wire
  serialization. Existing in-process code paths unchanged.

---

## [v0.2.0] — 2026-07-04 — Thirsty CLI + brand polish

### Added
- **`thirsty` CLI** at `thirsty-ai-builder/cli/`. A local coding
  agent that talks to the ThirstyAI Builder backend. Single
  `pip install -e thirsty-ai-builder/cli` puts `thirsty` on PATH.
  REPL, one-shot, three named model profiles (precise / balanced /
  creative), session persistence to `~/.thirsty-ai-builder/sessions/`.
- **7 backend tool endpoints** at `/api/tools/{read,write,edit,shell,
  grep,listdir,appstore}`. Opt-in via `THIRSTY_AI_TOOLS_ENABLED=1`.
  `write` and `shell` require a `confirm_token` generated by
  `POST /api/tools/confirm` — the CLI prints a 6-digit code, the
  user types it back. 60s TTL, fingerprint-bound to (tool, args).
- **Shell blocklist** as defence in depth: `rm -rf /`, dd to
  /dev/, mkfs, fork bombs, shutdown/reboot/halt, chmod -R 000,
  chown -R /. 12 patterns.
- **Skill system**: `~/.thirsty-ai-builder/skills/<name>/SKILL.md`
  with YAML frontmatter (name, description, tools). CLI matches on
  token overlap with the user message and injects the body into the
  system prompt.
- **Self-improvement loop**: `thirsty skill distill --last N` reads
  the last N session JSONs, extracts repeated tool sequences
  appearing `--min-occurrences` (default 3) times, and writes them
  as draft skills to `_drafts/`. User reviews with `thirsty skill
  approve <name>` (promotes to live) or `thirsty skill reject
  <name>` (deletes).
- **3 starter skills**: `code-review`, `refactor-planner`,
  `release-runbook`. Ship under `thirsty-ai-builder/cli/starter_skills/`
  for the user to copy into `~/.thirsty-ai-builder/skills/`.
- **4 new App Store tools**: `code-stats`, `dependency-audit`,
  `license-fit-checker`, `session-distill`.
- **28 new tests**: 16 CLI unit tests (config, session, skills,
  confirm), 12 tool-endpoint tests. Total 184, 0 failures.
- **`docs/CLI.md`**: full reference for the `thirsty` command,
  every subcommand, every activation step.
- **README badge row** on both READMEs: license, status, Python,
  Node, Ollama, Mongo, Ed25519, SBOM, tests, security.

### Changed
- **Casing**: `ThirstyAi Builder` → `ThirstyAI Builder` everywhere
  display-facing. Module names (`thirsty_ai_builder_backend`) and
  Python package names stay snake_case. Repo-wide sweep: 50+ files
  touched. Test for `/api/` `product` field updated to match.
- **CBEP gate** (`scripts/verify_all.py`): added benchmark suite to
  the 15-step list and tightened the 15-item table in the root
  README so each step fits one line.

### Security
- Tools are opt-in: routes return 503 until
  `THIRSTY_AI_TOOLS_ENABLED=1` is set. The default is OFF.
- Confirm-token replay protection: 60s TTL, fingerprint-bound, not
  reusable across (tool, args) pairs.
- `_safe_relative_path` rejects absolute paths and `..` traversal.
  `1 MiB` body cap from the existing `RequestSizeLimitMiddleware`
  applies to every tool call.

---

## [v0.1.0] — 2026-07-04 — Documentation refresh

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
