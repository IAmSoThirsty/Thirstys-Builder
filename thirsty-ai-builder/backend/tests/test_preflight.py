from __future__ import annotations

import sys
import unittest
from pathlib import Path


BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from thirsty_ai_builder_backend import preflight  # noqa: E402


GOOD_ENV = {
    "CB_API_KEY": "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
    "THIRSTY_AI_REQUIRE_AUTH": "1",
    "MONGO_URL": "mongodb://mongo:27017/thirsty_ai_builder",
    "THIRSTY_AI_REQUIRE_MONGO": "1",
    "CORS_ORIGINS": "https://builder.example.com",
    "OLLAMA_HOST": "http://127.0.0.1:11434",
}


class ProductionPreflight(unittest.TestCase):
    def test_accepts_good_environment(self):
        self.assertEqual(preflight.validate_environment(GOOD_ENV), [])

    def test_rejects_missing_required_values(self):
        errors = preflight.validate_environment({})
        self.assertIn("CB_API_KEY is required", errors)
        self.assertIn("MONGO_URL is required", errors)
        self.assertIn("OLLAMA_HOST is required", errors)

    def test_rejects_weak_or_placeholder_token(self):
        env = {**GOOD_ENV, "CB_API_KEY": "local-verify-token"}
        errors = preflight.validate_environment(env)
        self.assertTrue(any("CB_API_KEY" in error for error in errors))

    def test_rejects_wildcard_cors(self):
        env = {**GOOD_ENV, "CORS_ORIGINS": "*"}
        errors = preflight.validate_environment(env)
        self.assertIn("CORS_ORIGINS must not contain * in production", errors)

    def test_rejects_disabled_fail_closed_flags(self):
        env = {**GOOD_ENV, "THIRSTY_AI_REQUIRE_AUTH": "0", "THIRSTY_AI_REQUIRE_MONGO": ""}
        errors = preflight.validate_environment(env)
        self.assertIn("THIRSTY_AI_REQUIRE_AUTH must be true/1/on/yes", errors)
        self.assertIn("THIRSTY_AI_REQUIRE_MONGO must be true/1/on/yes", errors)


if __name__ == "__main__":
    raise SystemExit(unittest.main())
