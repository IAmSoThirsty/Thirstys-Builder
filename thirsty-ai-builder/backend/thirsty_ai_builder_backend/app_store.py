"""Seed tool catalog for the App Store page.

Each tool is a single dict that the App Store page lists. Adding a row
to `SEED_TOOLS` makes the tool appear in the UI. The audit harness can
also enumerate this catalog to produce signed-PDF reports.
"""
from __future__ import annotations

from typing import Any

SEED_TOOLS: list[dict[str, Any]] = [
    {
        "id": "commander-audit",
        "name": "Commander Audit",
        "description": "Governance audit harness for the Constitutional Builder. "
        "Runs the canonical verify_all.py gate and produces a signed PDF report.",
        "category": "governance",
        "version": "0.1.0",
    },
    {
        "id": "little-dove",
        "name": "Little Dove",
        "description": "Quiet conversational assistant. Routes to the LLM provider "
        "configured at deploy time (Emergent or Anthropic).",
        "category": "assistant",
        "version": "1.0.0",
    },
    {
        "id": "holli",
        "name": "Holli",
        "description": "Holistic operations assistant. LLM-backed, audit-logged, "
        "with deterministic stub fallback when no key is configured.",
        "category": "assistant",
        "version": "1.0.0",
    },
    {
        "id": "rag-embedder",
        "name": "RAG Embedder",
        "description": "Retrieval-augmented generation pipeline. In-process vector "
        "store backed by Mongo for embeddings.",
        "category": "rag",
        "version": "0.2.0",
    },
    {
        "id": "marketing-copy",
        "name": "Marketing Copy Generator",
        "description": "LLM-backed marketing copy generator with brand-voice presets.",
        "category": "marketing",
        "version": "1.0.0",
    },
    {
        "id": "social-poster",
        "name": "Social Poster",
        "description": "Cross-post to connected social channels. Credential management "
        "is environment-variable driven; no secrets stored in Mongo.",
        "category": "social",
        "version": "0.1.0",
    },
    {
        "id": "business-manager",
        "name": "Business Manager",
        "description": "Operations dashboard: clients, invoices, deliverables. "
        "Mongo-backed CRUD with audit log per write.",
        "category": "operations",
        "version": "1.0.0",
    },
]


def get_tool_by_id(tool_id: str) -> dict[str, Any] | None:
    for tool in SEED_TOOLS:
        if tool["id"] == tool_id:
            return tool
    return None
