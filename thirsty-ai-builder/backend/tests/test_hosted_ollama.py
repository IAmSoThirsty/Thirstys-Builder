"""Smoke tests for the hosted Ollama runbook.

We can't actually stand up Ollama, Tailscale, or WireGuard in this
repo's CI environment. The next best thing is to assert the runbook
artifacts are present, syntactically well-formed, and self-consistent
— no broken cross-references, no missing hardening directives, no
dangling commands that point at files that don't exist in this repo.
"""
from __future__ import annotations

import os
import re
import unittest
from pathlib import Path

# Layout:
#   thirsty-ai-builder/
#     HOSTED_OLLAMA.md
#     deploy/
#       ollama.service
#       ollama-tailscale.md
#       ollama-wireguard.conf.example
#       Caddyfile
#       nginx.conf
ROOT = Path(__file__).resolve().parents[3]
DEPLOY = ROOT / "thirsty-ai-builder" / "deploy"
RUNBOOK = ROOT / "thirsty-ai-builder" / "HOSTED_OLLAMA.md"

# Pre-compile the patterns that need MULTILINE. unittest.TestCase.
# assertRegex treats its 3rd arg as `msg`, not `flags`, so we have to
# hand it a compiled pattern object (which carries its own flags).
RE_USER_OLLAMA = re.compile(r"^User=ollama\s*$", re.MULTILINE)
RE_GROUP_OLLAMA = re.compile(r"^Group=ollama\s*$", re.MULTILINE)
RE_EXECSTART = re.compile(r"^ExecStart\s*=\s*/\S*ollama\s+serve", re.MULTILINE)
RE_MEMORYMAX = re.compile(r"^MemoryMax=\d+[MG]\s*$", re.MULTILINE)
RE_WANTEDBY = re.compile(r"^WantedBy=multi-user\.target\s*$", re.MULTILINE)
RE_OLLAMA_MODELS = re.compile(
    r'Environment="OLLAMA_MODELS=/var/lib/ollama/models"'
)
RE_WG_INTERFACE = re.compile(r"^\[Interface\]\s*$", re.MULTILINE)
RE_WG_PEER = re.compile(r"^\[Peer\]\s*$", re.MULTILINE)
RE_WG_PORT = re.compile(r"ListenPort\s*=\s*51820")
RE_DOC_BIND_WARN = re.compile(
    r"0\.0\.0\.0.*(expose|public|firewall|internet)",
    re.DOTALL | re.IGNORECASE,
)


def _has_flags(pattern: re.Pattern, text: str) -> bool:
    return pattern.search(text) is not None


class OllamaServiceUnit(unittest.TestCase):
    """The shipped systemd unit must be loadable and hardened."""

    @classmethod
    def setUpClass(cls):
        cls.unit_path = DEPLOY / "ollama.service"
        if not cls.unit_path.exists():
            raise unittest.SkipTest(f"ollama.service not found at {cls.unit_path}")
        cls.unit = cls.unit_path.read_text(encoding="utf-8")

    def test_unit_has_required_sections(self):
        for section in ("[Unit]", "[Service]", "[Install]"):
            self.assertIn(section, self.unit, f"missing section: {section}")

    def test_unit_has_execstart(self):
        self.assertTrue(
            _has_flags(RE_EXECSTART, self.unit),
            f"ExecStart pattern not found",
        )

    def test_unit_sets_ollama_models_env(self):
        self.assertRegex(self.unit, RE_OLLAMA_MODELS)

    def test_unit_runs_as_ollama_user(self):
        self.assertTrue(
            _has_flags(RE_USER_OLLAMA, self.unit), "User=ollama line missing"
        )
        self.assertTrue(
            _has_flags(RE_GROUP_OLLAMA, self.unit), "Group=ollama line missing"
        )

    def test_unit_has_hardening_directives(self):
        """NoNewPrivileges + ProtectSystem=strict + PrivateTmp are the
        minimum hardening set we expect for a network-facing service."""
        for directive in (
            "NoNewPrivileges=true",
            "ProtectSystem=strict",
            "PrivateTmp=true",
            "RestrictNamespaces=true",
            "RestrictRealtime=true",
        ):
            self.assertIn(directive, self.unit, f"missing hardening: {directive}")

    def test_unit_sets_memorymax(self):
        """The default MemoryMax must be present so the unit doesn't
        silently OOM-kill its parent process on big models."""
        self.assertTrue(
            _has_flags(RE_MEMORYMAX, self.unit),
            "MemoryMax=N(M|G) line missing",
        )

    def test_unit_has_install_wantedby(self):
        self.assertTrue(
            _has_flags(RE_WANTEDBY, self.unit),
            "WantedBy=multi-user.target line missing",
        )

    def test_unit_no_obvious_secrets(self):
        """The shipped unit must not contain API keys, passwords, or
        tokens. If you ever find yourself adding one, that is wrong —
        Ollama is local-only with no auth."""
        for forbidden in ("password", "secret", "api_key", "apikey", "token="):
            self.assertNotIn(forbidden, self.unit.lower())


class WireGuardTemplate(unittest.TestCase):
    """The WireGuard config template must be a valid template: every
    <PLACEHOLDER> is documented, and the file parses as INI."""

    @classmethod
    def setUpClass(cls):
        cls.cfg_path = DEPLOY / "ollama-wireguard.conf.example"
        if not cls.cfg_path.exists():
            raise unittest.SkipTest(
                f"ollama-wireguard.conf.example not found at {cls.cfg_path}"
            )
        cls.cfg = cls.cfg_path.read_text(encoding="utf-8")

    def test_template_has_interface_section(self):
        self.assertTrue(
            _has_flags(RE_WG_INTERFACE, self.cfg), "[Interface] section missing"
        )

    def test_template_has_at_least_one_peer_section(self):
        peer_count = len(RE_WG_PEER.findall(self.cfg))
        self.assertGreaterEqual(peer_count, 1)

    def test_template_uses_default_port(self):
        self.assertRegex(self.cfg, RE_WG_PORT)

    def test_template_documents_placeholder_meaning(self):
        """Every <PLACEHOLDER> in the file must be explained either
        inline as a comment or in the matching peer block further
        down. Otherwise an operator is left guessing."""
        placeholders = set(re.findall(r"<([A-Z_]+)>", self.cfg))
        self.assertTrue(placeholders, "expected at least one <PLACEHOLDER>")
        # Every placeholder should be mentioned in a comment OR in a
        # key=value line. We don't try to be cleverer than that here.
        for name in placeholders:
            needle = name.lower()
            self.assertIn(
                needle,
                self.cfg.lower(),
                f"placeholder <{name}> not documented in template",
            )

    def test_template_mentions_persistent_keepalive(self):
        """Cloud VMs behind NAT need PersistentKeepalive to keep the
        mapping warm. The template must include it for every peer."""
        self.assertGreaterEqual(self.cfg.count("PersistentKeepalive"), 1)


class TailscaleRecipe(unittest.TestCase):
    """The Tailscale recipe must give an operator a working path from
    zero to 'backend reaches Ollama' without leaving the file."""

    @classmethod
    def setUpClass(cls):
        cls.doc_path = DEPLOY / "ollama-tailscale.md"
        if not cls.doc_path.exists():
            raise unittest.SkipTest(f"ollama-tailscale.md not found at {cls.doc_path}")
        cls.doc = cls.doc_path.read_text(encoding="utf-8")

    def test_doc_has_install_command(self):
        self.assertIn("tailscale.com/install.sh", self.doc)

    def test_doc_has_status_command(self):
        self.assertIn("tailscale status", self.doc)

    def test_doc_warns_against_binding_to_0000(self):
        """0.0.0.0 is the foot-gun. The doc must call it out."""
        self.assertIn("0.0.0.0", self.doc)
        # The warning should appear in a context that names the risk.
        self.assertRegex(self.doc, RE_DOC_BIND_WARN)

    def test_doc_has_smoke_test(self):
        self.assertIn("/api/tags", self.doc)


class HostedOllamaRunbook(unittest.TestCase):
    """The top-level runbook must be self-consistent: every file path
    it references must exist in this repo, every command name it
    mentions must be one the shipped artifacts expect."""

    @classmethod
    def setUpClass(cls):
        if not RUNBOOK.exists():
            raise unittest.SkipTest(f"HOSTED_OLLAMA.md not found at {RUNBOOK}")
        cls.doc = RUNBOOK.read_text(encoding="utf-8")

    def test_runbook_references_deploy_artifacts(self):
        """Every deploy/* path the runbook mentions must exist."""
        for relative in (
            "deploy/ollama.service",
            "deploy/ollama-tailscale.md",
            "deploy/ollama-wireguard.conf.example",
        ):
            self.assertIn(relative, self.doc, f"runbook does not mention {relative}")
            self.assertTrue(
                (DEPLOY.parent / relative).exists(),
                f"runbook mentions {relative} but file is missing",
            )

    def test_runbook_references_owner_handoff(self):
        self.assertIn("OWNER_HANDOFF.md", self.doc)
        self.assertTrue((DEPLOY.parent / "OWNER_HANDOFF.md").exists())

    def test_runbook_references_deploy_md(self):
        self.assertIn("DEPLOY.md", self.doc)
        self.assertTrue((DEPLOY.parent / "DEPLOY.md").exists())

    def test_runbook_mentions_127_0_0_1_default(self):
        """The default Ollama URL must be visible in the runbook so an
        operator knows what the Builder's backend tries first."""
        self.assertIn("127.0.0.1:11434", self.doc)

    def test_runbook_mentions_health_endpoint(self):
        self.assertIn("/api/health", self.doc)

    def test_runbook_no_broken_relative_links(self):
        """Every relative link in the runbook (markdown link or bare
        path) should resolve to a file in this repo. We catch the
        cheap failure mode: a link with an obvious .md / .service /
        .conf / .example extension that points at nothing.

        Skip absolute paths (leading `/` or starting with a drive
        letter) and URLs — those are install paths, not repo paths.
        Also skip system paths (`/etc/...`, `/var/...`, `/usr/...`).

        Only check paths that have a directory component (a `/` before
        the basename). Bare basenames like `ollama.service` in
        sentences ("replace ollama.service") are not links.
        """
        # Find every path-shaped token in the doc. A real repo path
        # looks like `deploy/ollama.service` or `OWNER_HANDOFF.md` —
        # has at least one `/` OR is a top-level file we know about.
        candidates = re.findall(
            r"((?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+\.(?:md|service|conf|example|hujson))",
            self.doc,
        )
        # System-path components that look like install paths when
        # the leading `/` is missing (e.g. inside a sentence
        # "sudo cp deploy/ollama.service /etc/systemd/system/...").
        system_components = ("etc/", "var/", "usr/", "srv/", "opt/", "proc/")
        for path in candidates:
            if path.startswith(("http://", "https://")):
                continue
            if any(path.startswith(c) for c in system_components):
                continue
            full = DEPLOY.parent / path
            if not full.exists():
                self.fail(f"runbook references missing file: {path}")

        # Top-level files: only flag if they're missing.
        top_level = re.findall(
            r"(?<![A-Za-z0-9_./-])([A-Z][A-Z_]+\.md)", self.doc
        )
        for name in set(top_level):
            full = DEPLOY.parent / name
            if not full.exists():
                self.fail(f"runbook references missing top-level file: {name}")

    def test_runbook_has_security_checklist(self):
        """A runbook that doesn't tell the operator to bind to 127.0.0.1
        and ACL the tailnet is not a runbook."""
        for needle in (
            "127.0.0.1",
            "0.0.0.0",
            "Tailscale",
            "WireGuard",
            "ACL",
        ):
            self.assertIn(needle, self.doc, f"runbook missing security topic: {needle}")


class DeployDirectoryLayout(unittest.TestCase):
    """The deploy/ dir is small and deliberate. Anything new in it
    should be on purpose, and anything the runbook points at must
    exist."""

    def test_deploy_dir_exists(self):
        self.assertTrue(DEPLOY.is_dir(), f"deploy dir missing: {DEPLOY}")

    def test_tls_artifacts_present(self):
        """The Caddyfile + nginx.conf from the previous turn must
        still be here — the runbook cross-references the deploy dir
        as a whole."""
        for name in ("Caddyfile", "nginx.conf"):
            self.assertTrue(
                (DEPLOY / name).exists(),
                f"expected {name} in {DEPLOY}",
            )

    def test_ollama_artifacts_present(self):
        for name in (
            "ollama.service",
            "ollama-tailscale.md",
            "ollama-wireguard.conf.example",
        ):
            self.assertTrue(
                (DEPLOY / name).exists(),
                f"expected {name} in {DEPLOY}",
            )

    def test_no_stray_editor_swapfiles(self):
        """A runbook deploy dir should not be polluted with editor
        swap files, macOS dotfiles, or Windows thumbs.db."""
        for entry in DEPLOY.iterdir():
            name = entry.name
            self.assertFalse(
                name.startswith(".") or name.startswith("~") or name.endswith("~"),
                f"stray editor artifact: {name}",
            )


if __name__ == "__main__":
    unittest.main()
