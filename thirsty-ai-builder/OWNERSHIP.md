# Ownership

**Owner:** Jeremy Karrick
**Entity:** Thirsty's Projects LLC
**Entity Number:** 14694374-0160
**Registered Agent:** Entity Protect Registered Agent Services LLC, 169 W 2710 S Circle, STE 202A-65, Saint George, UT 84790-7205
**Contact:** founderoftp@thirstysprojects.com

## Registered Assets

| Asset | Location | Registered With |
|---|---|---|
| ThirstyAI Builder source code | `thirsty-ai-builder/` (this repository) | Owner + LICENSE + OWNERSHIP.md |
| ThirstyAI Builder design system | `thirsty-ai-builder/design_guidelines.json` | Owner + UI footer attribution |
| ThirstyAI Builder audit letterhead | `backend/thirsty_ai_builder_backend/letterhead.py` | Owner + SHA-256 attestation per PDF |
| ThirstyAI Builder ownership block | `backend/thirsty_ai_builder_backend/ownership.py` | `/api/ownership`, X-Owner headers, every signed PDF |
| Constitutional Builder Engineering Program (CBEP) | repository root | License + Commander audit log |

## Public-Facing Attribution

Every deployment must display, in a user-visible location, the canonical
ownership line. The `/api/ownership` endpoint and the `/about` page
return the full block. The frontend footer renders the copyright line
on every page. Every signed audit PDF embeds the entity number and
the SHA-256 attestation of the audit body.

## Rights Statement

This software is registered to Thirsty's Projects LLC. No third party
may sublicense, resell, fork for redistribution, or remove the
attribution. Independent developers may be engaged to extend the
software under written agreement with the owner; the LICENSE
explicitly forbids redistribution without written permission.

## Disputes

Send all disputes, takedown requests, and legal correspondence to the
registered agent at the address above, with a copy to
`founderoftp@thirstysprojects.com`.
