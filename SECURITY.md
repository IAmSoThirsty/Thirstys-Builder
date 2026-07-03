# Security Policy

This repository contains two products with separate security policies:

- **Constitutional Builder (CBEP)** — at the repo root. See `commander/audit-log.md` for past security-relevant decisions and `spec/volume-07-security-architecture.md` for the kernel's threat model.
- **ThirstyAi Builder** — at `thirsty-ai-builder/`. See [`thirsty-ai-builder/SECURITY.md`](thirsty-ai-builder/SECURITY.md) for the disclosure policy, supported versions, and hardening checklist for the FastAPI backend.

## Reporting a vulnerability

**Email:** founderoftp@thirstysprojects.com
**Subject prefix:** `[security]`

Both products share the same disclosure channel. Mention which product the report is about in the subject line (e.g. `[security][thirsty-ai]`).

See the per-product `SECURITY.md` for triage timelines, disclosure policy, and what to expect.

## Coordinated disclosure

- Acknowledgement within 72 hours.
- Triage within 7 days for Critical / High severity.
- 90-day disclosure window. Fix lands first; advisory is published when the fix ships or on a coordinated date.
- Credit available on request.
