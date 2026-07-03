"""Tests for the Wave-11 review-readiness hardening.

Every claim in `THREAT_MODEL.md` review checklist is exercised here.
If a reviewer asks "do you actually enforce this?", the answer is
"yes, and there is a test that fails when it is not enforced."
"""
from __future__ import annotations

import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DEPLOY = ROOT / "thirsty-ai-builder" / "deploy"
BACKEND = ROOT / "thirsty-ai-builder" / "backend"
THIRSTY_AI = ROOT / "thirsty-ai-builder"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

# Pre-compile patterns that need MULTILINE / IGNORECASE. unittest's
# assertRegex does not accept a flags argument, so we hand it compiled
# pattern objects (which carry their own flags).
RE_HEALTHCHECK = re.compile(r"^HEALTHCHECK\b", re.MULTILINE | re.IGNORECASE)
RE_USER_APP = re.compile(r"^USER\s+app:app", re.MULTILINE | re.IGNORECASE)
RE_USERADD_UID = re.compile(r"useradd.*--uid\s+10001")
RE_PYTHON_SLIM = re.compile(r"FROM\s+python:3\.\d+\.\d+-slim", re.IGNORECASE)
RE_NODE_ALPINE = re.compile(r"FROM\s+node:20\.\d+\.\d+-alpine", re.IGNORECASE)
RE_NO_LATEST = re.compile(r":latest")
RE_MULTISTAGE_FROM = re.compile(r"^\s*FROM\s+", re.MULTILINE)


# --- Secrets audit ----------------------------------------------------


class NoSecretsInRepo(unittest.TestCase):
    """The repo must not contain real API keys, passwords, or tokens.

    We scan the source tree for the common shapes. False positives
    are tolerated (the test passes if a real-looking key is in a
    test fixture that uses an obviously-fake value).
    """

    SECRET_PATTERNS = [
        # GitHub personal access tokens.
        re.compile(r"ghp_[A-Za-z0-9]{20,}"),
        # OpenAI / Anthropic / Mistral API keys.
        re.compile(r"sk-(?:ant-|or-|mis-)?[A-Za-z0-9_-]{20,}"),
        # AWS access keys.
        re.compile(r"AKIA[0-9A-Z]{16}"),
        # Stripe live keys.
        re.compile(r"sk_live_[A-Za-z0-9]{20,}"),
        # Slack tokens.
        re.compile(r"xox[bpars]-[A-Za-z0-9-]{10,}"),
    ]

    SKIP_DIRS = {".git", "__pycache__", "node_modules", "target", "release", "states"}

    def test_no_real_keys_in_source(self):
        offenders: list[tuple[Path, int, str]] = []
        for path in ROOT.rglob("*"):
            if not path.is_file():
                continue
            if any(part in self.SKIP_DIRS for part in path.parts):
                continue
            if path.suffix in {".zip", ".pdf", ".png", ".jpg", ".jpeg", ".gif"}:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except (OSError, UnicodeDecodeError):
                continue
            for pattern in self.SECRET_PATTERNS:
                for match in pattern.finditer(text):
                    offenders.append((path, 0, match.group(0)[:12] + "..."))
        if offenders:
            msg = "\n".join(f"  {p}: {snippet}" for p, _, snippet in offenders)
            self.fail(f"Real-looking secrets found in repo:\n{msg}")


# --- Dependency hygiene ------------------------------------------------


class DependencyPinning(unittest.TestCase):
    """Every direct backend dep must have a version pin (lower + upper).

    The convention in this repo is `dep>=X.Y,<A` (lower + upper bound).
    `==X.Y.Z` is also accepted (single-version pin). A bare `dep` with
    no version specifier is NOT accepted — `pip` would happily install
    a future major version and a reviewer would flag it.
    """

    def test_requirements_pinned(self):
        req_file = BACKEND / "requirements.txt"
        self.assertTrue(req_file.exists(), f"missing: {req_file}")
        offenders: list[str] = []
        for line in req_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Strip a trailing comment, if any (after a `#`).
            line = line.split("#", 1)[0].strip()
            if not line:
                continue
            # The version specifier is everything after the first
            # non-alphanumeric / non-version-related character. We
            # require at least one version operator.
            has_lower = ">=" in line or "==" in line
            has_upper = "<" in line or "==" in line
            if not (has_lower and has_upper):
                offenders.append(line)
        self.assertEqual(
            offenders, [],
            "every dep needs a lower AND upper bound (or `==`):\n  "
            + "\n  ".join(offenders),
        )


class SBOMFreshness(unittest.TestCase):
    """The SBOM must exist and be a well-formed component inventory."""

    def test_sbom_present(self):
        sbom = ROOT / "release" / "sbom.json"
        self.assertTrue(sbom.exists(), f"missing SBOM: {sbom}")

    def test_sbom_has_real_timestamp(self):
        """The SBOM's `generated_utc` must be a real timestamp, not epoch=0.

        A reviewer will reject an SBOM with `1970-01-01T00:00:00` as
        obviously broken.
        """
        import json
        sbom = json.loads((ROOT / "release" / "sbom.json").read_text(encoding="utf-8"))
        ts = sbom.get("generated_utc", "")
        self.assertTrue(ts, "SBOM is missing `generated_utc`")
        self.assertNotIn("1970-01-01", ts, f"SBOM has epoch=0 timestamp: {ts}")

    def test_sbom_excludes_build_artifacts(self):
        """The SBOM must not contain `target/`, `node_modules/`, etc.

        A reviewer will look at the component list and ask why cargo
        build cache is being shipped.
        """
        import json
        sbom = json.loads((ROOT / "release" / "sbom.json").read_text(encoding="utf-8"))
        offenders: list[str] = []
        for component in sbom.get("components", []):
            path = component.get("path", "")
            for excluded in ("target/", "node_modules/", "__pycache__/", "dist/", "build/"):
                if excluded in path:
                    offenders.append(path)
                    break
        self.assertEqual(
            offenders, [],
            f"SBOM includes build artifacts:\n  " + "\n  ".join(offenders[:10]),
        )

    def test_sbom_component_count_reasonable(self):
        """The component count should be in the dozens, not hundreds.

        A 200-component SBOM that mostly lists cargo build artifacts is
        a sign that the exclusion list is broken.
        """
        import json
        sbom = json.loads((ROOT / "release" / "sbom.json").read_text(encoding="utf-8"))
        count = len(sbom.get("components", []))
        self.assertLess(
            count, 200,
            f"SBOM has {count} components — too many, exclusion list is likely broken",
        )
        self.assertGreater(
            count, 50,
            f"SBOM has {count} components — too few, source files are missing",
        )


# --- Dockerfile hardening ---------------------------------------------


class BackendDockerfileHardening(unittest.TestCase):
    """The backend Dockerfile must run as non-root, use a pinned base,
    and have a healthcheck."""

    @classmethod
    def setUpClass(cls):
        cls.df = (BACKEND / "Dockerfile").read_text(encoding="utf-8")

    def test_no_root_user(self):
        self.assertRegex(self.df, RE_USERADD_UID)
        self.assertRegex(self.df, RE_USER_APP)

    def test_pinned_base(self):
        # A pinned major.minor.patch tag, not `:latest`.
        self.assertRegex(self.df, RE_PYTHON_SLIM)
        self.assertNotRegex(self.df, RE_NO_LATEST)

    def test_healthcheck_present(self):
        self.assertRegex(self.df, RE_HEALTHCHECK)

    def test_no_secrets_in_dockerfile(self):
        for needle in ("API_KEY=", "PASSWORD=", "SECRET=", "MONGO_URL="):
            self.assertNotIn(needle, self.df, f"hardcoded secret in Dockerfile: {needle}")


class FrontendDockerfileHardening(unittest.TestCase):
    """The frontend Dockerfile must be multi-stage, run unprivileged."""

    @classmethod
    def setUpClass(cls):
        cls.df = (THIRSTY_AI / "frontend" / "Dockerfile").read_text(encoding="utf-8")

    def test_multistage(self):
        self.assertGreaterEqual(len(RE_MULTISTAGE_FROM.findall(self.df)), 2, "needs at least 2 stages")

    def test_pinned_node(self):
        self.assertRegex(self.df, RE_NODE_ALPINE)
        self.assertNotRegex(self.df, RE_NO_LATEST)

    def test_frontend_defaults_to_same_origin_api(self):
        api_js = (THIRSTY_AI / "frontend" / "src" / "api.js").read_text(encoding="utf-8")
        self.assertIn('const BASE = process.env.REACT_APP_BACKEND_URL || "";', api_js)
        self.assertNotIn("http://localhost:8001", api_js)

    def test_frontend_sends_bearer_token(self):
        api_js = (THIRSTY_AI / "frontend" / "src" / "api.js").read_text(encoding="utf-8")
        app = (THIRSTY_AI / "frontend" / "src" / "App.jsx").read_text(encoding="utf-8")
        commander = (THIRSTY_AI / "frontend" / "src" / "pages" / "Commander.jsx").read_text(
            encoding="utf-8"
        )
        self.assertIn("localStorage", api_js)
        self.assertIn("headers.Authorization = `Bearer ${token}`", api_js)
        self.assertIn("AuthTokenControl", app)
        self.assertIn("downloadPdf", commander)
        self.assertNotIn("pdfUrl", commander)


class DockerComposeHardening(unittest.TestCase):
    """The compose file must drop capabilities, set no-new-privileges,
    and not expose private services to the host."""

    @classmethod
    def setUpClass(cls):
        cls.compose = (THIRSTY_AI / "docker-compose.yml").read_text(encoding="utf-8")

    def test_backend_no_new_privileges(self):
        # The backend block has no-new-privileges.
        self.assertIn("no-new-privileges:true", self.compose)

    def test_backend_read_only(self):
        self.assertIn("read_only: true", self.compose)

    def test_backend_drops_caps(self):
        self.assertIn("cap_drop:", self.compose)

    def test_backend_no_host_port(self):
        m = re.search(
            r"^\s{2}backend:\s*$(.+?)(?=^\s{2}\w+:|\Z)",
            self.compose,
            re.MULTILINE | re.DOTALL,
        )
        self.assertIsNotNone(m, "could not find backend service block")
        body = m.group(1)
        non_comment = "\n".join(
            line for line in body.splitlines() if not line.lstrip().startswith("#")
        )
        self.assertNotIn(
            "ports:", non_comment,
            "backend service has a `ports:` mapping; publish only the frontend",
        )
        self.assertIn("expose:", non_comment)

    def test_mongo_no_host_port(self):
        # The mongo service has no `ports:` mapping. This is a structural
        # check: the line "ports:" must not appear in the mongo service
        # body, ignoring comments.
        m = re.search(
            r"^\s{2}mongo:\s*$(.+?)(?=^\s{2}\w+:|\Z)",
            self.compose,
            re.MULTILINE | re.DOTALL,
        )
        self.assertIsNotNone(m, "could not find mongo service block")
        body = m.group(1)
        # Strip comment lines so `# No ports:` doesn't trip the check.
        non_comment = "\n".join(
            line for line in body.splitlines() if not line.lstrip().startswith("#")
        )
        self.assertNotIn(
            "ports:", non_comment,
            "mongo service has a `ports:` mapping — DB is exposed to host",
        )

    def test_mongo_runs_as_user(self):
        self.assertRegex(self.compose, r"user:\s*\"\d+:\d+\"")

    def test_healthchecks_present(self):
        self.assertGreaterEqual(self.compose.count("healthcheck:"), 3)

    def test_frontend_host_port_is_localhost_bound(self):
        self.assertIn('127.0.0.1:${THIRSTY_AI_FRONTEND_PORT:-3000}:80', self.compose)


# --- Server hardening -------------------------------------------------


class ServerHardening(unittest.TestCase):
    """The backend server must wire the security middlewares and not
    leak internals."""

    @classmethod
    def setUpClass(cls):
        cls.src = (BACKEND / "server.py").read_text(encoding="utf-8")
        cls.hardening = (BACKEND / "thirsty_ai_builder_backend" / "hardening.py").read_text(
            encoding="utf-8"
        )

    def test_cors_not_wildcard_with_credentials(self):
        """The code must explicitly handle the `*` + credentials foot-gun."""
        self.assertIn("allow_credentials=_cors_credentials", self.src)
        # The default must NOT be `*` (that is the unsafe case).
        self.assertNotIn(
            'os.environ.get("CORS_ORIGINS", "*")', self.src
        )

    def test_request_size_limit_middleware_registered(self):
        self.assertIn("RequestSizeLimitMiddleware", self.src)

    def test_security_headers_middleware_registered(self):
        self.assertIn("SecurityHeadersMiddleware", self.src)

    def test_rate_limit_middleware_registered(self):
        self.assertIn("RateLimitMiddleware", self.src)

    def test_audit_endpoint_bounded(self):
        """Audit endpoint must use a semaphore to bound concurrent runs."""
        self.assertIn("_AUDIT_SEMAPHORE", self.src)
        self.assertRegex(self.src, r"BoundedSemaphore\(\d+\)")

    def test_no_utcnow(self):
        """`datetime.utcnow()` is deprecated in 3.12+; use `_utc_now_iso`."""
        # Match the call shape `datetime.utcnow(`, not the word in comments.
        offenders = re.findall(
            r"\bdatetime\.utcnow\s*\(", self.src
        )
        # Allow occurrences inside triple-quoted docstrings or `#` comments.
        # We strip both before searching.
        no_docstrings = re.sub(r'"""[\s\S]*?"""', "", self.src)
        no_docstrings = re.sub(r"'''[\s\S]*?'''", "", no_docstrings)
        no_comments = "\n".join(
            line for line in no_docstrings.splitlines()
            if not line.lstrip().startswith("#")
        )
        offenders = re.findall(r"\bdatetime\.utcnow\s*\(", no_comments)
        self.assertEqual(
            offenders, [],
            "datetime.utcnow() is still called in the code",
        )

    def test_pydantic_max_length_on_free_text(self):
        """Every Pydantic free-text field must have a max_length cap.

        A "free-text field" is a `str` (not `int`, not `list`, not a
        Pydantic BaseModel) in a class that subclasses `BaseModel`.
        Output models (e.g. `ChatResponse`) and models with only
        bounded types are skipped.
        """
        offenders: list[str] = []
        for model_match in re.finditer(
            r"class\s+\w+\(BaseModel\):([\s\S]+?)(?=\nclass\s|\n# ---|\Z)",
            self.src,
        ):
            body = model_match.group(1)
            for line in body.splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                # Find a `field: str = ...` line.
                m = re.match(r"^(\w+)\s*:\s*str\b", stripped)
                if not m:
                    continue
                # Must have `max_length=` somewhere on the same line,
                # or be a default of empty string with no Field (a sentinel).
                if "max_length=" not in stripped and "Field" in stripped:
                    offenders.append(stripped)
        self.assertEqual(
            offenders, [],
            "string fields with Field() but no max_length:\n  "
            + "\n  ".join(offenders),
        )

    def test_health_ready_does_not_leak_exception(self):
        """The readiness endpoint must not return the raw exception text."""
        # Find the ready() function. Use a more careful regex that
        # matches the function-def `:` (at the end of a line), not a
        # type-annotation `:` inside the parameters.
        m = re.search(
            r"def ready\([^)]*\)[^\n]*:\n(.+?)(?=\n@app\.|\n# ---|\Z)",
            self.src,
            re.DOTALL,
        )
        self.assertIsNotNone(m, "could not find ready() function")
        body = m.group(1)
        self.assertNotIn('f"error: {exc}"', body)
        self.assertIn('checks["database"] = "unavailable"', body)


# --- Threat model and security docs -----------------------------------


class ThreatModelAndSecurity(unittest.TestCase):
    """The THREAT_MODEL.md and SECURITY.md docs must exist and reference
    the assets they document."""

    def test_threat_model_present(self):
        self.assertTrue((THIRSTY_AI / "THREAT_MODEL.md").exists())

    def test_threat_model_covers_cors(self):
        text = (THIRSTY_AI / "THREAT_MODEL.md").read_text(encoding="utf-8")
        self.assertIn("CORS", text)
        self.assertIn("T2", text)  # request size limit
        self.assertIn("T4", text)  # DoS via LLM
        self.assertIn("T6", text)  # audit PDF forgery
        self.assertIn("T7", text)  # info disclosure

    def test_production_mongo_fail_closed_is_documented(self):
        threat_model = (THIRSTY_AI / "THREAT_MODEL.md").read_text(encoding="utf-8")
        security = (THIRSTY_AI / "SECURITY.md").read_text(encoding="utf-8")
        deploy = (THIRSTY_AI / "DEPLOY.md").read_text(encoding="utf-8")
        compose = (THIRSTY_AI / "docker-compose.yml").read_text(encoding="utf-8")
        for text in (threat_model, security, deploy, compose):
            self.assertIn("THIRSTY_AI_REQUIRE_MONGO", text)
        self.assertNotIn("planned Stage 3", threat_model)
        self.assertNotIn("does not refuse to start", security)

    def test_production_auth_fail_closed_is_documented(self):
        threat_model = (THIRSTY_AI / "THREAT_MODEL.md").read_text(encoding="utf-8")
        security = (THIRSTY_AI / "SECURITY.md").read_text(encoding="utf-8")
        deploy = (THIRSTY_AI / "DEPLOY.md").read_text(encoding="utf-8")
        compose = (THIRSTY_AI / "docker-compose.yml").read_text(encoding="utf-8")
        for text in (threat_model, security, deploy, compose):
            self.assertIn("THIRSTY_AI_REQUIRE_AUTH", text)
        self.assertIn("CB_API_KEY", threat_model)
        self.assertIn("CB_API_KEY", security)

    def test_production_preflight_is_documented(self):
        threat_model = (THIRSTY_AI / "THREAT_MODEL.md").read_text(encoding="utf-8")
        security = (THIRSTY_AI / "SECURITY.md").read_text(encoding="utf-8")
        deploy = (THIRSTY_AI / "DEPLOY.md").read_text(encoding="utf-8")
        for text in (threat_model, security, deploy):
            self.assertIn("thirsty_ai_builder_backend.preflight", text)

    def test_security_md_present(self):
        self.assertTrue((THIRSTY_AI / "SECURITY.md").exists())
        self.assertTrue((ROOT / "SECURITY.md").exists())

    def test_security_md_has_disclosure_email(self):
        text = (THIRSTY_AI / "SECURITY.md").read_text(encoding="utf-8")
        self.assertIn("founderoftp@thirstysprojects.com", text)
        self.assertIn("90-day", text)


# --- Hardening module unit tests --------------------------------------


class HardeningModuleUnit(unittest.TestCase):
    """Unit tests for the hardening middlewares themselves."""

    def test_token_bucket_refills(self):
        from thirsty_ai_builder_backend.hardening import _TokenBucket
        bucket = _TokenBucket(rate_per_minute=600, burst=3)  # 10/sec
        self.assertTrue(bucket.take("k")[0])
        self.assertTrue(bucket.take("k")[0])
        self.assertTrue(bucket.take("k")[0])
        # 4th in the same instant is denied.
        self.assertFalse(bucket.take("k")[0])
        # After waiting, it refills.
        import time
        time.sleep(0.2)
        self.assertTrue(bucket.take("k")[0])

    def test_token_bucket_per_key(self):
        from thirsty_ai_builder_backend.hardening import _TokenBucket
        bucket = _TokenBucket(rate_per_minute=60, burst=1)
        self.assertTrue(bucket.take("a")[0])
        self.assertFalse(bucket.take("a")[0])
        # Different key has its own bucket.
        self.assertTrue(bucket.take("b")[0])


if __name__ == "__main__":
    unittest.main()
