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
        "description": "Quiet conversational assistant. Routes to the local Ollama "
        "model configured at deploy time (OLLAMA_MODEL).",
        "category": "assistant",
        "version": "1.0.0",
    },
    {
        "id": "holli",
        "name": "Holli",
        "description": "Holistic operations assistant. Local-Ollama backed, "
        "audit-logged. Returns 503 if Ollama is unreachable.",
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
    {
        "id": "code-stats",
        "name": "Code Stats",
        "description": "Lines of code, file count, and language breakdown "
        "(by file extension) for a pasted path. Read-only, no shell exec.",
        "category": "developer",
        "version": "0.1.0",
    },
    {
        "id": "dependency-audit",
        "name": "Dependency Audit",
        "description": "Runs pip-audit and npm audit against the user's "
        "manifests and posts a summary. Read-only; no patches applied.",
        "category": "security",
        "version": "0.1.0",
    },
    {
        "id": "license-fit-checker",
        "name": "License Fit Checker",
        "description": "Reads a LICENSE file at a user-supplied path, "
        "classifies it (Apache-2.0, MIT, BSD, Proprietary, Other), and "
        "returns a one-line 'can you ship a fork' answer.",
        "category": "legal",
        "version": "0.1.0",
    },
    {
        "id": "session-distill",
        "name": "Session Distill",
        "description": "Reads the last N Thirsty CLI sessions, extracts "
        "repeated tool sequences, and writes them as draft skills. "
        "User reviews and approves each draft before it loads. The "
        "self-improvement loop for the Thirsty CLI.",
        "category": "developer",
        "version": "0.1.0",
    },
]


def get_tool_by_id(tool_id: str) -> dict[str, Any] | None:
    for tool in SEED_TOOLS:
        if tool["id"] == tool_id:
            return tool
    return None
