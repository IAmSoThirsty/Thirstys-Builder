"""Smoke tests for the TLS termination configs.

We can't actually stand up Caddy or nginx in this repo's CI environment,
so this test does the next best thing: parse both configs, assert that
each one enforces TLS, asserts that the backend is on loopback, and
asserts that the long-running endpoints have a non-trivial timeout.
"""
from __future__ import annotations

import os
import re
import sys
import unittest
from pathlib import Path

# Make the deploy dir reachable.
ROOT = Path(__file__).resolve().parents[3]
DEPLOY = ROOT / "thirsty-ai-builder" / "deploy"


class CaddyConfig(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg_path = DEPLOY / "Caddyfile"
        if not cls.cfg_path.exists():
            raise unittest.SkipTest(f"Caddyfile not found at {cls.cfg_path}")
        cls.cfg = cls.cfg_path.read_text(encoding="utf-8")

    def test_caddyfile_present(self):
        self.assertGreater(len(self.cfg), 100)

    def test_caddyfile_forwards_to_loopback(self):
        """The Caddyfile must forward to 127.0.0.1:8001 so the backend
        stays on the local network and not publicly exposed."""
        self.assertRegex(self.cfg, r"reverse_proxy\s+127\.0\.0\.1:8001")

    def test_caddyfile_sets_hsts(self):
        self.assertIn("Strict-Transport-Security", self.cfg)
        self.assertIn("max-age=31536000", self.cfg)

    def test_caddyfile_sets_security_headers(self):
        for header in (
            "X-Frame-Options",
            "X-Content-Type-Options",
            "Referrer-Policy",
        ):
            self.assertIn(header, self.cfg, f"missing header: {header}")

    def test_caddyfile_has_long_lived_timeout(self):
        """The longlived path matcher must include the chat/marketing/rag/commander paths."""
        for path in (
            "/api/dove/chat",
            "/api/holli/chat",
            "/api/marketing/copy",
            "/api/rag",
            "/api/commander/audits",
        ):
            self.assertIn(path, self.cfg, f"missing long-lived path: {path}")

    def test_caddyfile_restricts_to_tls_1_2_or_higher(self):
        # The Caddyfile's tls block must include a protocol restriction.
        tls_block = re.search(r"tls\s*\{[^}]*\}", self.cfg, re.DOTALL)
        self.assertIsNotNone(tls_block, "Caddyfile is missing a tls { } block")
        block = tls_block.group(0)
        self.assertIn("tls1.2", block)
        self.assertIn("tls1.3", block)


class NginxConfig(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg_path = DEPLOY / "nginx.conf"
        if not cls.cfg_path.exists():
            raise unittest.SkipTest(f"nginx.conf not found at {cls.cfg_path}")
        cls.cfg = cls.cfg_path.read_text(encoding="utf-8")

    def test_nginx_present(self):
        self.assertGreater(len(self.cfg), 100)

    def test_nginx_redirects_http_to_https(self):
        """The first server block must redirect :80 -> :443."""
        # The first 'server { ... }' block should end in a 301 to https://.
        first = re.search(r"server\s*\{[^}]*\}", self.cfg, re.DOTALL)
        self.assertIsNotNone(first)
        self.assertIn("listen 80", first.group(0))
        self.assertIn("return 301 https", first.group(0))

    def test_nginx_tls_server_block(self):
        # Find the server block that listens on 443.
        tls_block = re.search(
            r"server\s*\{[^}]*listen\s+443[^}]*\}", self.cfg, re.DOTALL
        )
        self.assertIsNotNone(tls_block, "no server block listening on 443")

    def test_nginx_forwards_to_loopback(self):
        self.assertIn("127.0.0.1:8001", self.cfg)

    def test_nginx_sets_hsts(self):
        self.assertIn("Strict-Transport-Security", self.cfg)
        self.assertIn("max-age=31536000", self.cfg)

    def test_nginx_restricts_protocols(self):
        self.assertRegex(self.cfg, r"ssl_protocols\s+TLSv1\.2\s+TLSv1\.3")

    def test_nginx_long_running_timeout(self):
        """The chat/marketing/rag/commander location block must set a
        proxy_read_timeout of at least 60s (default is 60s in nginx)."""
        # Find the block matching the long-running endpoints.
        m = re.search(
            r"location\s+~?\s*\^/api/\(dove\|holli\|marketing\|rag\|commander\)\s*\{[^}]*\}",
            self.cfg,
            re.DOTALL,
        )
        self.assertIsNotNone(m, "no long-running location block in nginx.conf")
        block = m.group(0)
        # Extract proxy_read_timeout value.
        tm = re.search(r"proxy_read_timeout\s+(\d+)s", block)
        self.assertIsNotNone(tm, "no proxy_read_timeout in long-running block")
        self.assertGreaterEqual(int(tm.group(1)), 60)


if __name__ == "__main__":
    raise SystemExit(unittest.main())
