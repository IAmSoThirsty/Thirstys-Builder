"""Tests for the auth layer + the /api/health and /api/health/ready endpoints."""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest import mock

# Make the backend package importable when this file is run via
# `python -m unittest discover -s .../tests -p test_auth.py`.
_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

# We need a CB_API_KEY set for the tests that exercise the auth dependency.
# Tests that verify the "no key configured" path clear it.
TEST_TOKEN = "test-token-for-unit-tests-only"


def _client():
    """Build a TestClient with a fresh env."""
    from fastapi.testclient import TestClient
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    # Clear the sys.modules cache for the server so a fresh `app` is built
    # with the current env vars.
    for mod in list(sys.modules):
        if mod.startswith("server") or mod.startswith("thirsty_ai_builder_backend"):
            del sys.modules[mod]
    import server  # noqa: E402
    return TestClient(server.app)


class AuthPublicPaths(unittest.TestCase):
    def setUp(self):
        # Auth is configured for the rest of the suite.
        os.environ["CB_API_KEY"] = TEST_TOKEN

    def test_health_no_token(self):
        c = _client()
        r = c.get("/api/health")
        self.assertEqual(r.status_code, 200)

    def test_ownership_no_token(self):
        c = _client()
        r = c.get("/api/ownership")
        self.assertEqual(r.status_code, 200)

    def test_root_no_token(self):
        c = _client()
        r = c.get("/")
        self.assertEqual(r.status_code, 200)

    def test_docs_no_token(self):
        c = _client()
        # FastAPI docs is at /docs, not /api/docs.
        r = c.get("/docs")
        self.assertEqual(r.status_code, 200)

    def test_health_reports_auth_configured(self):
        c = _client()
        r = c.get("/api/health")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["auth_configured"])

    def test_health_ready_ok_when_auth_and_db_ok(self):
        c = _client()
        with mock.patch("thirsty_ai_builder_backend.llm.list_models", return_value=["qwen2.5-coder:7b"]):
            r = c.get("/api/health/ready")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["status"], "ready")
        self.assertEqual(body["checks"]["auth"], "configured")
        self.assertEqual(body["checks"]["ollama"], "ok")
        self.assertEqual(body["checks"]["database"], "ok")

    def test_health_ready_503_when_ollama_down(self):
        c = _client()
        with mock.patch("thirsty_ai_builder_backend.llm.list_models", return_value=[]):
            r = c.get("/api/health/ready")
        self.assertEqual(r.status_code, 503)
        self.assertIn("unavailable", r.json()["checks"]["ollama"])


class AuthProtectedPaths(unittest.TestCase):
    def setUp(self):
        os.environ["CB_API_KEY"] = TEST_TOKEN

    def test_dove_chat_rejects_no_token(self):
        c = _client()
        r = c.post("/api/dove/chat", json={"message": "hi"})
        self.assertEqual(r.status_code, 401)
        self.assertEqual(r.headers.get("www-authenticate"), "Bearer")
        self.assertIn("Missing Authorization", r.json()["detail"])

    def test_dove_chat_rejects_wrong_scheme(self):
        c = _client()
        r = c.post(
            "/api/dove/chat",
            json={"message": "hi"},
            headers={"Authorization": "Basic dXNlcjpwYXNz"},
        )
        self.assertEqual(r.status_code, 401)
        self.assertIn("Bearer <token>", r.json()["detail"])

    def test_dove_chat_rejects_wrong_token(self):
        c = _client()
        r = c.post(
            "/api/dove/chat",
            json={"message": "hi"},
            headers={"Authorization": "Bearer wrong-key"},
        )
        self.assertEqual(r.status_code, 401)
        self.assertEqual(r.json()["detail"], "Invalid token.")

    def test_dove_chat_accepts_correct_token(self):
        c = _client()
        # Force a stub for the chat by making Ollama unavailable at the
        # module level.
        with mock.patch("thirsty_ai_builder_backend.llm.list_models", return_value=[]):
            r = c.post(
                "/api/dove/chat",
                json={"message": "hello"},
                headers={"Authorization": f"Bearer {TEST_TOKEN}"},
            )
        # With no Ollama, the chat endpoint should 503 — not 401.
        self.assertIn(r.status_code, (200, 503))

    def test_run_audit_requires_token(self):
        c = _client()
        r = c.post("/api/commander/audits/run", json={"target": "x"})
        self.assertEqual(r.status_code, 401)

    def test_run_audit_accepts_token(self):
        c = _client()
        r = c.post(
            "/api/commander/audits/run",
            json={"target": "x", "title": "auth-test"},
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        self.assertIn(r.status_code, (200, 500))  # 500 only if subprocess dies; 200 if it works

    def test_audit_pdf_requires_token(self):
        c = _client()
        r = c.get("/api/commander/audits/no-such-id/pdf")
        self.assertEqual(r.status_code, 401)

    def test_appstore_install_requires_token(self):
        c = _client()
        r = c.post("/api/appstore/install", json={"tool_id": "commander-audit"})
        self.assertEqual(r.status_code, 401)

    def test_rag_embed_requires_token(self):
        c = _client()
        r = c.post("/api/rag/embed", json={"text": "x", "source": "y"})
        self.assertEqual(r.status_code, 401)

    def test_rag_query_requires_token(self):
        c = _client()
        r = c.post("/api/rag/query", json={"query": "x", "k": 1})
        self.assertEqual(r.status_code, 401)

    def test_business_create_requires_token(self):
        c = _client()
        r = c.post(
            "/api/business/clients",
            json={"name": "Acme", "contact_email": "a@b.com"},
        )
        self.assertEqual(r.status_code, 401)

    def test_marketing_requires_token(self):
        c = _client()
        r = c.post(
            "/api/marketing/copy",
            json={"topic": "x", "voice": "professional", "audience": "y"},
        )
        self.assertEqual(r.status_code, 401)


class AuthNoKeyConfigured(unittest.TestCase):
    def setUp(self):
        os.environ.pop("CB_API_KEY", None)

    def test_protected_returns_503_when_no_key(self):
        c = _client()
        r = c.post("/api/dove/chat", json={"message": "hi"})
        self.assertEqual(r.status_code, 503)
        self.assertIn("CB_API_KEY", r.json()["detail"])

    def test_public_still_works(self):
        c = _client()
        r = c.get("/api/health")
        self.assertEqual(r.status_code, 200)

    def test_auth_configured_returns_false(self):
        from thirsty_ai_builder_backend import auth
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertFalse(auth.configured())

    def test_auth_configured_returns_true(self):
        from thirsty_ai_builder_backend import auth
        with mock.patch.dict(os.environ, {"CB_API_KEY": "x"}):
            self.assertTrue(auth.configured())


class AuthTokenHelpers(unittest.TestCase):
    def test_generate_token_is_unique(self):
        from thirsty_ai_builder_backend import auth
        a = auth.generate_token()
        b = auth.generate_token()
        self.assertNotEqual(a, b)
        self.assertGreaterEqual(len(a), 32)

    def test_constant_time_equals_true(self):
        from thirsty_ai_builder_backend import auth
        with mock.patch.dict(os.environ, {"CB_API_KEY": "abc"}):
            self.assertTrue(auth.constant_time_equals("abc", "abc"))

    def test_constant_time_equals_false(self):
        from thirsty_ai_builder_backend import auth
        with mock.patch.dict(os.environ, {"CB_API_KEY": "abc"}):
            self.assertFalse(auth.constant_time_equals("abc", "xyz"))


import sys  # noqa: E402  (used by _client)


if __name__ == "__main__":
    raise SystemExit(unittest.main())
