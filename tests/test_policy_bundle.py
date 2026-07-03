import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "source"))

from constitutional_builder import load_policy_bundle, migrate_legacy_policy_list  # noqa: E402


class PolicyBundleTests(unittest.TestCase):
    def test_load_valid_policy_bundle(self):
        bundle = load_policy_bundle(Path(__file__).resolve().parents[1] / "examples" / "policy-bundle.json")
        self.assertEqual(bundle.bundle_id, "example-policy-bundle")
        self.assertEqual(len(bundle.rules), 2)

    def test_duplicate_policy_id_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "bundle.json"
            path.write_text(
                json.dumps(
                    {
                        "bundle_id": "bad",
                        "version": "1.0",
                        "rules": [
                            {"policy_id": "dup", "effect": "allow", "operation": "echo"},
                            {"policy_id": "dup", "effect": "deny", "operation": "echo"},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                load_policy_bundle(path)

    def test_migrate_legacy_policy_list(self):
        bundle = migrate_legacy_policy_list(
            bundle_id="legacy",
            policies=[
                {
                    "policy_id": "allow",
                    "effect": "allow",
                    "operation": "echo",
                    "resource": "demo",
                    "subject_id": "operator",
                }
            ],
        )
        self.assertEqual(bundle.version, "1.0")
        self.assertEqual(bundle.rules[0].policy_id, "allow")


if __name__ == "__main__":
    unittest.main()
