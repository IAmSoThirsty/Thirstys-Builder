"""Owner / IP constants for the ThirstyAi Builder.

These are returned by the `/api/` ownership block, the `/about` page,
the footer, every signed PDF, the LICENSE, and the OWNERSHIP.md. If
anyone forks or copies this code, the ownership block travels with it.
"""
from __future__ import annotations

OWNER_NAME = "Jeremy Karrick"
OWNER_EMAIL = "karrick1995@gmail.com"
ENTITY_NAME = "Thirsty's Projects LLC"
ENTITY_NUMBER = "14694374-0160"
PRINCIPAL_OFFICE = "1450 South West Temple Street, A402, Salt Lake City, UT 84115-5203"
REGISTERED_AGENT = "Entity Protect Registered Agent Services LLC, 169 W 2710 S Circle, STE 202A-65, Saint George, UT 84790-7205"
COPYRIGHT_LINE = (
    f"\u00a9 2026 {OWNER_NAME} / {ENTITY_NAME}. "
    f"Entity #{ENTITY_NUMBER}. All rights reserved."
)
PRODUCT_NAME = "ThirstyAi Builder"


def ownership_block() -> dict[str, str]:
    """The canonical ownership block, returned by every /api/ response and
    embedded in the UI footer and signed PDFs."""
    return {
        "product": PRODUCT_NAME,
        "owner_name": OWNER_NAME,
        "owner_email": OWNER_EMAIL,
        "entity_name": ENTITY_NAME,
        "entity_number": ENTITY_NUMBER,
        "principal_office": PRINCIPAL_OFFICE,
        "registered_agent": REGISTERED_AGENT,
        "copyright": COPYRIGHT_LINE,
        "license": "Proprietary. All rights reserved.",
    }
