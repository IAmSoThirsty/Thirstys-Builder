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
import threading
import uuid
from datetime import timezone
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Allow `python server.py` from the backend/ dir.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from thirsty_ai_builder_backend import (  # noqa: E402
    app_store,
    auth,
    db,
    hardening,
    letterhead,
    llm,
    ownership,
)


app = FastAPI(title=ownership.PRODUCT_NAME, version="1.0.0")

# --- CORS ----------------------------------------------------------------
# CORS is a security-sensitive knob. We refuse to start with the
# combination of `allow_origins=["*"]` AND `allow_credentials=True`,
# which is the most common cross-origin foot-gun in FastAPI. Operators
# set `CORS_ORIGINS` to a comma-separated explicit list of allowed
# origins. The default is `["http://localhost:3000"]` for local dev.
_cors_raw = os.environ.get("CORS_ORIGINS", "http://localhost:3000").strip()
CORS_ORIGINS = [o.strip() for o in _cors_raw.split(",") if o.strip()]
if "*" in CORS_ORIGINS:
    # Browser will refuse the response when credentials are present,
    # but the server still happily serves CORS headers to anyone.
    # We force credentials off in that case so the request simply
    # fails the CORS check on the client side.
    _cors_credentials = False
else:
    _cors_credentials = True
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=_cors_credentials,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=600,
)

# --- Hardening middlewares (order matters: outer runs first) ------------
# 1. Request size cap (rejects before any work is done).
# 2. Security headers (every response gets them).
# 3. Rate limit (token bucket per (ip, route prefix)).
app.add_middleware(hardening.SecurityHeadersMiddleware)
app.add_middleware(hardening.RateLimitMiddleware)
app.add_middleware(hardening.RequestSizeLimitMiddleware)

if auth.require_auth() and not auth.configured():
    raise RuntimeError("THIRSTY_AI_REQUIRE_AUTH=1 requires CB_API_KEY")

# Process-singleton DB client.
_client = db.get_client()
_database = db.get_database(_client)

# Bound the number of concurrent audit runs. A 600-second subprocess
# multiplied by unbounded concurrency is a CPU and memory hole.
_AUDIT_SEMAPHORE = threading.BoundedSemaphore(2)


def _utc_now_iso() -> str:
    """Return current UTC time as an ISO 8601 string with `Z` suffix.

    Python 3.12+ deprecates `datetime.utcnow()`. Use the timezone-aware
    constructor everywhere.
    """
    return dt.datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


# ---------- auth dependency ----------
# Routes marked with this dependency require a valid Bearer token.
# Public routes (health, ownership, docs) are unauthenticated by design.
Authed = Depends(auth.verify_bearer)


# ---------- ownership block on every response ----------
@app.middleware("http")
async def _add_ownership_header(request, call_next):
    response = await call_next(request)
    response.headers["X-Owner"] = ownership.OWNER_NAME
    response.headers["X-Entity"] = ownership.ENTITY_NAME
    response.headers["X-Entity-Number"] = ownership.ENTITY_NUMBER
    return response


# ---------- request/response models ----------
# Every free-text field has a max_length. Pydantic enforces the cap
# before the handler runs, so the LLM (or anything else downstream)
# is never handed an unbounded string. These caps are tight but not
# arbitrary: they cover any reasonable user input for the named
# endpoint and reject obvious abuse.
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000)
    history: list[dict[str, str]] = Field(default_factory=list, max_length=50)


class ChatResponse(BaseModel):
    reply: str
    model: str
    provider: str


class ToolInstallRequest(BaseModel):
    tool_id: str = Field(..., min_length=1, max_length=128)


class BusinessClientRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    contact_email: str = Field(..., min_length=3, max_length=320)
    notes: str = Field(default="", max_length=4000)


class SocialPostRequest(BaseModel):
    channel: str = Field(..., min_length=1, max_length=64)
    text: str = Field(..., min_length=1, max_length=2000)


class MarketingRequest(BaseModel):
    topic: str = Field(..., min_length=1, max_length=200)
    voice: str = Field(default="professional", max_length=64)
    audience: str = Field(default="general", max_length=64)


class RAGEmbedRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=16000)
    source: str = Field(default="manual", max_length=128)


class RAGQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    k: int = Field(default=3, ge=1, le=10)


# ---------- /api/ownership ----------
@app.get("/api/ownership")
def get_ownership() -> dict[str, str]:
    return ownership.ownership_block()


# ---------- /api/health ----------
@app.get("/api/health")
def health() -> dict[str, Any]:
    """Liveness: process is up. Always 200 if the server is responsive."""
    return {
        "status": "ok",
        "product": ownership.PRODUCT_NAME,
        "version": "1.0.0",
        "llm_provider": llm.configured_provider(),
        "database_backend": db.backend_kind(),
        "auth_configured": auth.configured(),
        "ownership": ownership.ownership_block(),
    }


@app.get("/api/health/ready")
def ready(response: Response) -> dict[str, Any]:
    """Readiness: verifies the backend can reach its dependencies.

    Returns 503 with per-dependency detail when not ready. Point a load
    balancer / orchestrator readiness probe here.

    Internal exception messages are NOT exposed to the client. They
    are logged for operators and the response carries only an opaque
    "unavailable" string. A reviewer can correlate via the
    server logs.
    """
    checks: dict[str, str] = {}
    # LLM (Ollama).
    provider = llm.configured_provider()
    checks["ollama"] = "ok" if provider == "ollama" else f"unavailable ({provider})"
    # DB. Dev/test may use the in-memory backend. Production compose
    # sets THIRSTY_AI_REQUIRE_MONGO=1, so import/startup already fails
    # unless real Mongo is configured and reachable.
    try:
        _database["__healthcheck__"].insert_one({"_": "ping"})
        checks["database"] = "ok"
    except Exception as exc:  # noqa: BLE001
        # Log the actual error; return only the high-level status.
        import logging
        logging.getLogger("thirsty_ai_builder.ready").warning(
            "database healthcheck failed: %s", exc
        )
        checks["database"] = "unavailable"
    # Auth.
    checks["auth"] = "configured" if auth.configured() else "missing CB_API_KEY"
    ready_status = all(v == "ok" or v == "configured" for v in checks.values())
    if not ready_status:
        response.status_code = 503
    return {"status": "ready" if ready_status else "unavailable", "checks": checks}


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
def list_audits(_: str = Authed) -> dict[str, Any]:
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
def get_audit_pdf(audit_id: str, _: str = Authed) -> Response:
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
def run_audit(req: AuditRunRequest, _: str = Authed) -> dict[str, Any]:
    """Run a governance audit against the requested target and persist a signed PDF.

    The default target is the CBEP repo: runs `verify_all.py` via
    subprocess and captures stdout/stderr. Custom targets are allowed
    for future expansion (e.g. external repositories audited by the
    Commander workflow).

    Concurrency is bounded by a BoundedSemaphore so a flood of audit
    requests cannot fork an unbounded number of 600-second subprocesses.
    """
    if not _AUDIT_SEMAPHORE.acquire(blocking=False):
        raise HTTPException(
            status_code=429,
            detail="Too many concurrent audits. Retry shortly.",
        )
    try:
        return _run_audit_locked(req)
    finally:
        _AUDIT_SEMAPHORE.release()


def _run_audit_locked(req: AuditRunRequest) -> dict[str, Any]:
    audit_id = f"audit-{secrets.token_hex(8)}"
    title = req.title or f"Constitutional Builder Audit {_utc_now_iso()}"
    body_lines = [f"Target: {req.target}", f"Audit ID: {audit_id}", ""]
    sha = hashlib.sha256()
    sha.update(audit_id.encode("utf-8"))

    if req.target == "constitutional-builder":
        cbep_root = Path(__file__).resolve().parents[2]
        verify_script = cbep_root / "scripts" / "verify_all.py"
        if verify_script.exists():
            import subprocess

            try:
                completed = subprocess.run(
                    [sys.executable, str(verify_script)],
                    cwd=str(cbep_root),
                    check=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    timeout=600,
                )
            except subprocess.TimeoutExpired:
                body_lines.append("verify_all.py timed out after 600s.")
                completed = None
            except Exception as exc:  # noqa: BLE001
                # Never leak the exception text to the audit record or
                # the client. Log and continue.
                import logging
                logging.getLogger("thirsty_ai_builder.audit").error(
                    "verify_all.py failed to start: %s", exc
                )
                body_lines.append("verify_all.py could not be executed.")
                completed = None
            if completed is not None:
                body_lines.append("=== verify_all.py stdout ===")
                body_lines.append(completed.stdout[-8000:] if completed.stdout else "")
                body_lines.append("")
                body_lines.append(f"exit_code: {completed.returncode}")
                sha.update((completed.stdout or "").encode("utf-8", errors="replace"))
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
            "created_at": _utc_now_iso(),
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
def dove_chat(req: ChatRequest, _: str = Authed) -> ChatResponse:
    messages = list(req.history) + [{"role": "user", "content": req.message}]
    try:
        result = llm.chat(messages)
    except llm.LLMUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return ChatResponse(
        reply=result["content"],
        model=result["model"],
        provider=llm.configured_provider(),
    )


# ---------- /api/holli ----------
@app.post("/api/holli/chat")
def holli_chat(req: ChatRequest, _: str = Authed) -> ChatResponse:
    messages = list(req.history) + [{"role": "user", "content": req.message}]
    try:
        result = llm.chat(messages)
    except llm.LLMUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return ChatResponse(
        reply=result["content"],
        model=result["model"],
        provider=llm.configured_provider(),
    )


# ---------- /api/architecture ----------
@app.get("/api/architecture")
def architecture() -> dict[str, Any]:
    return {
        "frontend": "React 18 + Tailwind + Framer Motion. 11 pages.",
        "backend": "FastAPI on Python 3.11. Single-file server, modular subpackages.",
        "persistence": "MongoDB (Motor async client). In-memory stub for dev.",
        "llm": "Local Ollama server (OLLAMA_HOST). No external keys required.",
        "ci": "Rust CI auditor (cargo build) that gates PRs via the Commander.",
        "ownership": ownership.ownership_block(),
    }


# ---------- /api/appstore ----------
@app.get("/api/appstore/tools")
def list_tools(_: str = Authed) -> dict[str, Any]:
    return {"tools": app_store.SEED_TOOLS}


@app.post("/api/appstore/install")
def install_tool(req: ToolInstallRequest, _: str = Authed) -> dict[str, Any]:
    tool = app_store.get_tool_by_id(req.tool_id)
    if tool is None:
        raise HTTPException(status_code=404, detail="tool not found")
    install_id = f"install-{uuid.uuid4().hex[:8]}"
    _database["installs"].insert_one(
        {
            "id": install_id,
            "tool_id": req.tool_id,
            "tool_name": tool["name"],
            "installed_at": _utc_now_iso(),
        }
    )
    return {"id": install_id, "tool_id": req.tool_id, "status": "installed"}


@app.get("/api/appstore/installs")
def list_installs(_: str = Authed) -> dict[str, Any]:
    return {"installs": _database["installs"].find()}


# ---------- /api/business ----------
@app.post("/api/business/clients")
def create_client(req: BusinessClientRequest, _: str = Authed) -> dict[str, Any]:
    client_id = f"client-{uuid.uuid4().hex[:8]}"
    record = {
        "id": client_id,
        "name": req.name,
        "contact_email": req.contact_email,
        "notes": req.notes,
        "created_at": _utc_now_iso(),
    }
    _database["clients"].insert_one(record)
    return record


@app.get("/api/business/clients")
def list_clients(_: str = Authed) -> dict[str, Any]:
    return {"clients": _database["clients"].find()}


# ---------- /api/socials ----------
@app.post("/api/socials/posts")
def queue_social_post(req: SocialPostRequest, _: str = Authed) -> dict[str, Any]:
    post_id = f"post-{uuid.uuid4().hex[:8]}"
    _database["social_posts"].insert_one(
        {
            "id": post_id,
            "channel": req.channel,
            "text": req.text,
            "queued_at": _utc_now_iso(),
        }
    )
    return {"id": post_id, "channel": req.channel, "status": "queued"}


@app.get("/api/socials/posts")
def list_social_posts(_: str = Authed) -> dict[str, Any]:
    return {"posts": _database["social_posts"].find()}


# ---------- /api/marketing ----------
@app.post("/api/marketing/copy")
def marketing_copy(req: MarketingRequest, _: str = Authed) -> dict[str, Any]:
    prompt = (
        f"Write marketing copy on the topic: {req.topic}. "
        f"Voice: {req.voice}. Audience: {req.audience}. "
        "Three short variants, each <= 240 chars."
    )
    try:
        result = llm.chat([{"role": "user", "content": prompt}])
    except llm.LLMUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return {
        "topic": req.topic,
        "voice": req.voice,
        "audience": req.audience,
        "copy": result["content"],
        "provider": llm.configured_provider(),
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
def rag_embed(req: RAGEmbedRequest, _: str = Authed) -> dict[str, Any]:
    embed_id = f"emb-{uuid.uuid4().hex[:8]}"
    record = {
        "id": embed_id,
        "text": req.text,
        "source": req.source,
        "vector": _embed(req.text),
        "created_at": _utc_now_iso(),
    }
    _database["rag_embeddings"].insert_one(record)
    return {"id": embed_id, "source": req.source, "vector_dim": len(record["vector"])}


@app.post("/api/rag/query")
def rag_query(req: RAGQueryRequest, _: str = Authed) -> dict[str, Any]:
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
        try:
            result = llm.chat([{"role": "user", "content": prompt}])
        except llm.LLMUnavailable as exc:
            raise HTTPException(status_code=503, detail=str(exc))
        answer = result["content"]
        provider = llm.configured_provider()
    else:
        answer = "No documents have been embedded yet. POST /api/rag/embed first."
        provider = "none"
    return {
        "query": req.query,
        "matches": [
            {"id": item[1]["id"], "source": item[1]["source"], "score": float(item[0])}
            for item in top
        ],
        "answer": answer,
        "provider": provider,
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
    if not auth.configured():
        print(
            "WARNING: CB_API_KEY is not set. All authenticated routes will return 503.",
            flush=True,
        )
        print(
            "         Generate a token: python -c \"import secrets; print(secrets.token_urlsafe(32))\"",
            flush=True,
        )
        print(
            "         Then: set CB_API_KEY=<token> in .env and restart.",
            flush=True,
        )
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
