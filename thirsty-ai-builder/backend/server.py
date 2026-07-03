"""FastAPI server for the ThirstyAi Builder.

Single-file backend (per the owner hand-off). Every page in the
frontend has a corresponding route prefix here:
  /api/home              -- landing manifest
  /api/commander/*       -- audit list, run audit, sign PDF
  /api/dove/*            -- Little Dove assistant
  /api/holli/*           -- Holli assistant
  /api/architecture/*    -- system architecture description
  /api/appstore/*        -- tool catalog + per-tool actions
  /api/business/*        -- Business Manager CRUD
  /api/socials/*         -- social channel connections + post queue
  /api/marketing/*       -- copy generation
  /api/rag/*             -- RAG embed + query
  /api/about             -- ownership block
  /api/ownership         -- canonical ownership block
  /api/health            -- health probe
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import secrets
import sys
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Allow `python server.py` from the backend/ dir.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from thirsty_ai_builder_backend import (  # noqa: E402
    app_store,
    db,
    letterhead,
    llm,
    ownership,
)


app = FastAPI(title=ownership.PRODUCT_NAME, version="1.0.0")

CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Process-singleton DB client.
_client = db.get_client()
_database = db.get_database(_client)


# ---------- ownership block on every response ----------
@app.middleware("http")
async def _add_ownership_header(request, call_next):
    response = await call_next(request)
    response.headers["X-Owner"] = ownership.OWNER_NAME
    response.headers["X-Entity"] = ownership.ENTITY_NAME
    response.headers["X-Entity-Number"] = ownership.ENTITY_NUMBER
    return response


# ---------- request/response models ----------
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000)
    history: list[dict[str, str]] = Field(default_factory=list)


class ChatResponse(BaseModel):
    reply: str
    model: str
    provider: str
    stub: bool = False


class ToolInstallRequest(BaseModel):
    tool_id: str


class BusinessClientRequest(BaseModel):
    name: str
    contact_email: str
    notes: str = ""


class SocialPostRequest(BaseModel):
    channel: str
    text: str = Field(..., min_length=1, max_length=2000)


class MarketingRequest(BaseModel):
    topic: str
    voice: str = "professional"
    audience: str = "general"


class RAGEmbedRequest(BaseModel):
    text: str
    source: str = "manual"


class RAGQueryRequest(BaseModel):
    query: str
    k: int = 3


# ---------- /api/ownership ----------
@app.get("/api/ownership")
def get_ownership() -> dict[str, str]:
    return ownership.ownership_block()


# ---------- /api/health ----------
@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "product": ownership.PRODUCT_NAME,
        "version": "1.0.0",
        "llm_provider": llm.configured_provider(),
        "ownership": ownership.ownership_block(),
    }


# ---------- /api/home ----------
@app.get("/api/home")
def home() -> dict[str, Any]:
    return {
        "tagline": "Governed, auditable, owner-attested AI builder.",
        "pages": [
            "Home",
            "Commander",
            "Little Dove",
            "Holli",
            "Architecture",
            "App Store",
            "Business Manager",
            "Socials",
            "Marketing",
            "RAG",
            "About",
        ],
        "ownership": ownership.ownership_block(),
    }


# ---------- /api/commander ----------
@app.get("/api/commander/audits")
def list_audits() -> dict[str, Any]:
    audits = _database["audits"].find()
    return {
        "audits": [
            {
                "id": a.get("id"),
                "title": a.get("title"),
                "created_at": a.get("created_at"),
                "sha256": a.get("sha256"),
            }
            for a in audits
        ]
    }


@app.get("/api/commander/audits/{audit_id}/pdf")
def get_audit_pdf(audit_id: str) -> Response:
    audit = _database["audits"].find_one({"id": audit_id})
    if audit is None:
        raise HTTPException(status_code=404, detail="audit not found")
    return Response(
        content=audit["pdf_bytes"],
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{audit_id}.pdf"',
            "X-SHA256": audit["sha256"],
        },
    )


class AuditRunRequest(BaseModel):
    target: str = "constitutional-builder"
    title: str | None = None


@app.post("/api/commander/audits/run")
def run_audit(req: AuditRunRequest) -> dict[str, Any]:
    """Run a governance audit against the requested target and persist a signed PDF.

    The default target is the CBEP repo: runs `verify_all.py` via
    subprocess and captures stdout/stderr. Custom targets are allowed
    for future expansion (e.g. external repositories audited by the
    Commander workflow).
    """
    audit_id = f"audit-{secrets.token_hex(8)}"
    title = req.title or f"Constitutional Builder Audit {dt.datetime.utcnow().isoformat()}Z"
    body_lines = [f"Target: {req.target}", f"Audit ID: {audit_id}", ""]
    sha = hashlib.sha256()
    sha.update(audit_id.encode("utf-8"))

    if req.target == "constitutional-builder":
        cbep_root = Path(__file__).resolve().parents[2]
        verify_script = cbep_root / "scripts" / "verify_all.py"
        if verify_script.exists():
            import subprocess

            completed = subprocess.run(
                [sys.executable, str(verify_script)],
                cwd=str(cbep_root),
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=600,
            )
            body_lines.append("=== verify_all.py stdout ===")
            body_lines.append(completed.stdout[-8000:])
            body_lines.append("")
            body_lines.append(f"exit_code: {completed.returncode}")
            sha.update(completed.stdout.encode("utf-8", errors="replace"))
        else:
            body_lines.append("verify_all.py not present; recording stub audit.")
    else:
        body_lines.append("Custom target recorded without execution.")

    body_lines.append("")
    body_lines.append(f"SHA-256: {sha.hexdigest()}")
    body = "\n".join(body_lines)

    rendered = letterhead.render_audit_report(
        title=title, body=body, metadata={"audit_id": audit_id, "target": req.target}
    )
    _database["audits"].insert_one(
        {
            "id": audit_id,
            "title": title,
            "created_at": dt.datetime.utcnow().isoformat() + "Z",
            "sha256": rendered["sha256"],
            "pdf_bytes": rendered["pdf_bytes"],
            "target": req.target,
        }
    )
    return {
        "id": audit_id,
        "title": title,
        "sha256": rendered["sha256"],
        "ownership": ownership.ownership_block(),
    }


# ---------- /api/dove ----------
@app.post("/api/dove/chat")
def dove_chat(req: ChatRequest) -> ChatResponse:
    messages = list(req.history) + [{"role": "user", "content": req.message}]
    result = llm.chat(messages)
    return ChatResponse(
        reply=result["content"],
        model=result["model"],
        provider=llm.configured_provider(),
        stub=result.get("stub", False),
    )


# ---------- /api/holli ----------
@app.post("/api/holli/chat")
def holli_chat(req: ChatRequest) -> ChatResponse:
    messages = list(req.history) + [{"role": "user", "content": req.message}]
    result = llm.chat(messages, model="claude-sonnet-4-20250514")
    return ChatResponse(
        reply=result["content"],
        model=result["model"],
        provider=llm.configured_provider(),
        stub=result.get("stub", False),
    )


# ---------- /api/architecture ----------
@app.get("/api/architecture")
def architecture() -> dict[str, Any]:
    return {
        "frontend": "React 18 + Tailwind + Framer Motion. 11 pages.",
        "backend": "FastAPI on Python 3.11. Single-file server, modular subpackages.",
        "persistence": "MongoDB (Motor async client). In-memory stub for dev.",
        "llm": "Emergent Universal Key OR Anthropic key (env-driven).",
        "ci": "Rust CI auditor (cargo build) that gates PRs via the Commander.",
        "ownership": ownership.ownership_block(),
    }


# ---------- /api/appstore ----------
@app.get("/api/appstore/tools")
def list_tools() -> dict[str, Any]:
    return {"tools": app_store.SEED_TOOLS}


@app.post("/api/appstore/install")
def install_tool(req: ToolInstallRequest) -> dict[str, Any]:
    tool = app_store.get_tool_by_id(req.tool_id)
    if tool is None:
        raise HTTPException(status_code=404, detail="tool not found")
    install_id = f"install-{uuid.uuid4().hex[:8]}"
    _database["installs"].insert_one(
        {
            "id": install_id,
            "tool_id": req.tool_id,
            "tool_name": tool["name"],
            "installed_at": dt.datetime.utcnow().isoformat() + "Z",
        }
    )
    return {"id": install_id, "tool_id": req.tool_id, "status": "installed"}


@app.get("/api/appstore/installs")
def list_installs() -> dict[str, Any]:
    return {"installs": _database["installs"].find()}


# ---------- /api/business ----------
@app.post("/api/business/clients")
def create_client(req: BusinessClientRequest) -> dict[str, Any]:
    client_id = f"client-{uuid.uuid4().hex[:8]}"
    record = {
        "id": client_id,
        "name": req.name,
        "contact_email": req.contact_email,
        "notes": req.notes,
        "created_at": dt.datetime.utcnow().isoformat() + "Z",
    }
    _database["clients"].insert_one(record)
    return record


@app.get("/api/business/clients")
def list_clients() -> dict[str, Any]:
    return {"clients": _database["clients"].find()}


# ---------- /api/socials ----------
@app.post("/api/socials/posts")
def queue_social_post(req: SocialPostRequest) -> dict[str, Any]:
    post_id = f"post-{uuid.uuid4().hex[:8]}"
    _database["social_posts"].insert_one(
        {
            "id": post_id,
            "channel": req.channel,
            "text": req.text,
            "queued_at": dt.datetime.utcnow().isoformat() + "Z",
        }
    )
    return {"id": post_id, "channel": req.channel, "status": "queued"}


@app.get("/api/socials/posts")
def list_social_posts() -> dict[str, Any]:
    return {"posts": _database["social_posts"].find()}


# ---------- /api/marketing ----------
@app.post("/api/marketing/copy")
def marketing_copy(req: MarketingRequest) -> dict[str, Any]:
    prompt = (
        f"Write marketing copy on the topic: {req.topic}. "
        f"Voice: {req.voice}. Audience: {req.audience}. "
        "Three short variants, each <= 240 chars."
    )
    result = llm.chat([{"role": "user", "content": prompt}])
    return {
        "topic": req.topic,
        "voice": req.voice,
        "audience": req.audience,
        "copy": result["content"],
        "provider": llm.configured_provider(),
        "stub": result.get("stub", False),
    }


# ---------- /api/rag ----------
def _embed(text: str) -> list[float]:
    """Deterministic in-process embedding.

    Production would call an embedding model. For dev/CI, this is a
    stable 32-dim hash-based vector that allows end-to-end testing of
    the RAG pipeline without an embedding service.
    """
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return [b / 255.0 for b in digest] + [0.0] * (32 - len(digest))


def _cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b)) / (
        (sum(x * x for x in a) ** 0.5) * (sum(y * y for y in b) ** 0.5) + 1e-12
    )


@app.post("/api/rag/embed")
def rag_embed(req: RAGEmbedRequest) -> dict[str, Any]:
    embed_id = f"emb-{uuid.uuid4().hex[:8]}"
    record = {
        "id": embed_id,
        "text": req.text,
        "source": req.source,
        "vector": _embed(req.text),
        "created_at": dt.datetime.utcnow().isoformat() + "Z",
    }
    _database["rag_embeddings"].insert_one(record)
    return {"id": embed_id, "source": req.source, "vector_dim": len(record["vector"])}


@app.post("/api/rag/query")
def rag_query(req: RAGQueryRequest) -> dict[str, Any]:
    target = _embed(req.query)
    scored = []
    for record in _database["rag_embeddings"].find():
        score = _cosine(target, record["vector"])
        scored.append((score, record))
    scored.sort(reverse=True)
    top = scored[: max(1, min(req.k, 10))]
    context = "\n\n---\n\n".join(item[1]["text"] for item in top)
    if context:
        prompt = (
            f"Use the following context to answer the question.\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {req.query}\n\n"
            "If the context does not contain the answer, say so."
        )
        result = llm.chat([{"role": "user", "content": prompt}])
        answer = result["content"]
        provider = llm.configured_provider()
        stub = result.get("stub", False)
    else:
        answer = "No documents have been embedded yet. POST /api/rag/embed first."
        provider = "none"
        stub = True
    return {
        "query": req.query,
        "matches": [
            {"id": item[1]["id"], "source": item[1]["source"], "score": float(item[0])}
            for item in top
        ],
        "answer": answer,
        "provider": provider,
        "stub": stub,
    }


# ---------- /api/about ----------
@app.get("/api/about")
def about() -> dict[str, Any]:
    return {
        **ownership.ownership_block(),
        "deploy_paths": ["Railway", "Vercel + Render", "Fly.io", "VPS"],
        "support_email": ownership.OWNER_EMAIL,
        "license": "Proprietary. See LICENSE in the repo root.",
    }


# ---------- root ----------
@app.get("/")
def root() -> dict[str, Any]:
    return {
        "product": ownership.PRODUCT_NAME,
        "version": "1.0.0",
        "ownership": ownership.ownership_block(),
        "docs": "/api/docs",
    }


def main() -> None:
    import uvicorn

    port = int(os.environ.get("PORT", "8001"))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
