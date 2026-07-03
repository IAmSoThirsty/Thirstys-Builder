"""Tests for the /api/tools/* endpoints.

Run: PYTHONPATH=thirsty-ai-builder/backend python -m unittest thirsty-ai-builder.backend.tests.test_tools_endpoint
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient


# Make the backend package importable.
BACKEND_PKG = Path(__file__).resolve().parents[1] / "thirsty_ai_builder_backend"
sys.path.insert(0, str(BACKEND_PKG.parent))


class TestToolsEndpoint(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Required: CB_API_KEY + THIRSTY_AI_TOOLS_ENABLED=1
        os.environ["CB_API_KEY"] = "test-key-1234567890"
        os.environ.setdefault("THIRSTY_AI_REQUIRE_AUTH", "1")
        os.environ["THIRSTY_AI_TOOLS_ENABLED"] = "1"
        from server import app  # type: ignore
        cls.client = TestClient(app)
        cls.headers = {"Authorization": "Bearer test-key-1234567890"}

    def test_tools_disabled_by_default_without_env(self):
        # In a separate process, with the env var unset, the routes
        # should return 503. We simulate by patching.
        from server import app  # type: ignore
        import thirsty_ai_builder_backend.tools as tools_mod
        old = tools_mod.tools_enabled
        tools_mod.tools_enabled = lambda: False
        try:
            r = self.client.get("/api/tools/appstore", headers=self.headers)
            self.assertEqual(r.status_code, 503)
        finally:
            tools_mod.tools_enabled = old

    def test_appstore_lists_six_post_tools(self):
        r = self.client.get("/api/tools/appstore", headers=self.headers)
        self.assertEqual(r.status_code, 200)
        data = r.json()
        names = sorted(t["name"] for t in data["tools"])
        # 6 POST tools; /api/tools/appstore is the metadata endpoint itself
        self.assertEqual(names, ["edit", "grep", "listdir", "read", "shell", "write"])

    def test_write_requires_confirm_token(self):
        r = self.client.post(
            "/api/tools/write",
            json={"args": {"path": "test_write.txt", "content": "hi"}},
            headers=self.headers,
        )
        self.assertEqual(r.status_code, 403)

    def test_shell_requires_confirm_token(self):
        r = self.client.post(
            "/api/tools/shell",
            json={"args": {"command": "echo hello"}},
            headers=self.headers,
        )
        self.assertEqual(r.status_code, 403)

    def test_confirm_then_write_succeeds(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "subdir" / "out.txt"
            rel = str(target.relative_to(Path(tmp)))  # relative to cwd; backend's _safe_relative_path checks against path
            # Use a path under the current working directory to satisfy _safe_relative_path
            # (the backend's _safe_relative_path doesn't enforce a base dir, but
            # requires the path to be relative. We use a tmp path under cwd.)
            import os
            cwd = os.getcwd()
            target_abs = Path(cwd) / "_test_thirsty_tools_out.txt"
            rel = "_test_thirsty_tools_out.txt"
            try:
                args = {"path": rel, "content": "hello"}
                cr = self.client.post("/api/tools/confirm", json={"tool": "write", "args": args}, headers=self.headers)
                self.assertEqual(cr.status_code, 200, cr.text)
                code = cr.json()["code"]
                wr = self.client.post(
                    "/api/tools/write",
                    json={"args": args, "confirm_token": code},
                    headers=self.headers,
                )
                self.assertEqual(wr.status_code, 200, wr.text)
                self.assertTrue(target_abs.exists())
                self.assertEqual(target_abs.read_text(encoding="utf-8"), "hello")
            finally:
                if target_abs.exists():
                    target_abs.unlink()

    def test_shell_blocklist_rejects_rm_rf(self):
        # Use the same normalized args the shell handler will see.
        args = {"command": "rm -rf /", "cwd": "", "timeout_seconds": 30}
        cr = self.client.post("/api/tools/confirm", json={"tool": "shell", "args": args}, headers=self.headers)
        self.assertEqual(cr.status_code, 200, cr.text)
        code = cr.json()["code"]
        r = self.client.post(
            "/api/tools/shell",
            json={"args": args, "confirm_token": code},
            headers=self.headers,
        )
        self.assertEqual(r.status_code, 200, f"shell call: {r.text}")
        body = r.json()
        self.assertFalse(body["ok"], f"shell should have been blocked, got: {body}")
        self.assertIn("blocked", body["error"])

    def test_read_nonexistent_returns_error(self):
        r = self.client.post(
            "/api/tools/read",
            json={"path": "this_does_not_exist_xyz.txt"},
            headers=self.headers,
        )
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertFalse(body["ok"])
        self.assertIn("not found", body["error"])

    def test_grep_finds_pattern(self):
        import tempfile, os
        rel = "_test_thirsty_grep.txt"
        cwd = os.getcwd()
        target = Path(cwd) / rel
        target.write_text("hello world\nthe quick brown fox\nhello again\n", encoding="utf-8")
        try:
            r = self.client.post(
                "/api/tools/grep",
                json={"pattern": r"hello", "path": rel},
                headers=self.headers,
            )
            self.assertEqual(r.status_code, 200, r.text)
            body = r.json()
            self.assertTrue(body["ok"])
            self.assertEqual(body["result"]["count"], 2)
        finally:
            if target.exists():
                target.unlink()

    def test_listdir_lists_entries(self):
        import tempfile, os
        rel = "_test_thirsty_listdir"
        cwd = os.getcwd()
        d = Path(cwd) / rel
        d.mkdir(exist_ok=True)
        (d / "a.txt").write_text("x", encoding="utf-8")
        (d / "b").mkdir(exist_ok=True)
        try:
            r = self.client.post(
                "/api/tools/listdir",
                json={"path": rel},
                headers=self.headers,
            )
            self.assertEqual(r.status_code, 200, r.text)
            body = r.json()
            self.assertTrue(body["ok"])
            names = sorted(e["name"] for e in body["result"]["entries"])
            self.assertIn("a.txt", names)
            self.assertIn("b", names)
        finally:
            import shutil
            if d.exists():
                shutil.rmtree(d)

    def test_edit_replaces_expected_occurrences(self):
        import os
        cwd = os.getcwd()
        target = Path(cwd) / "_test_thirsty_tools_edit.txt"
        target.write_text("foo bar foo", encoding="utf-8")
        try:
            r = self.client.post(
                "/api/tools/edit",
                json={"path": "_test_thirsty_tools_edit.txt", "find": "foo", "replace": "BAZ", "expected_occurrences": 2},
                headers=self.headers,
            )
            self.assertEqual(r.status_code, 200, r.text)
            self.assertEqual(target.read_text(encoding="utf-8"), "BAZ bar BAZ")
        finally:
            if target.exists():
                target.unlink()

    def test_edit_refuses_on_mismatch(self):
        import os
        cwd = os.getcwd()
        target = Path(cwd) / "_test_thirsty_tools_edit_mismatch.txt"
        target.write_text("foo bar", encoding="utf-8")
        try:
            r = self.client.post(
                "/api/tools/edit",
                json={"path": "_test_thirsty_tools_edit_mismatch.txt", "find": "foo", "replace": "BAZ", "expected_occurrences": 5},
                headers=self.headers,
            )
            self.assertEqual(r.status_code, 200, r.text)
            body = r.json()
            self.assertFalse(body["ok"])
            self.assertIn("expected", body["error"])
        finally:
            if target.exists():
                target.unlink()

    def test_unauthed_request_returns_401_or_503(self):
        r = self.client.get("/api/tools/appstore")
        self.assertIn(r.status_code, (401, 503))


if __name__ == "__main__":
    unittest.main()
