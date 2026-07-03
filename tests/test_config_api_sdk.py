import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "source"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "sdk" / "python"))

from constitutional_builder.api import make_server  # noqa: E402
from constitutional_builder.config import build_kernel_from_config, load_config  # noqa: E402
from constitutional_builder_sdk import BuilderClient, BuilderClientError  # noqa: E402


class ConfigApiSdkTests(unittest.TestCase):
    def write_config(self, directory: Path) -> Path:
        config = {
            "audit_log_path": "audit.jsonl",
            "subjects": [
                {"subject_id": "operator", "display_name": "Operator", "roles": ["operator"]},
                {"subject_id": "auditor", "display_name": "Auditor", "roles": ["auditor"]},
            ],
            "policies": [
                {
                    "policy_id": "allow-operator-echo",
                    "effect": "allow",
                    "subject_id": "operator",
                    "operation": "echo",
                    "resource": "demo",
                },
                {
                    "policy_id": "deny-auditor",
                    "effect": "deny",
                    "subject_id": "auditor",
                    "operation": "*",
                    "resource": "*",
                    "reason": "read only",
                },
            ],
            "capabilities": [
                {
                    "grant_id": "operator-echo",
                    "subject_id": "operator",
                    "operation": "echo",
                    "resource": "demo",
                }
            ],
        }
        path = directory / "config.json"
        path.write_text(json.dumps(config), encoding="utf-8")
        return path

    def test_configured_kernel_file_audit_and_api_sdk(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config = load_config(self.write_config(Path(temp_dir)))
            kernel = build_kernel_from_config(config)
            server = make_server(kernel, "127.0.0.1", 0)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                host, port = server.server_address
                client = BuilderClient(f"http://{host}:{port}")

                decision = client.execute(
                    request_id="req-1",
                    subject_id="operator",
                    operation="echo",
                    resource="demo",
                    parameters={"message": "ok"},
                )
                self.assertEqual(decision["status"], "allowed")
                self.assertEqual(client.replay()["valid"], True)
                self.assertEqual(client.health()["audit_valid"], True)
                self.assertEqual(client.audit()["event_count"], 1)
                query = client.query("{ replay { valid eventCount reason } }")
                self.assertEqual(query["data"]["replay"]["valid"], True)
                self.assertEqual(query["data"]["replay"]["eventCount"], 1)
                grpc = client.grpc_compat("constitutional_builder.v1.BuilderService/Replay")
                self.assertEqual(grpc["valid"], True)
                self.assertEqual(grpc["event_count"], 1)

                with self.assertRaises(BuilderClientError):
                    client.execute(
                        request_id="req-2",
                        subject_id="auditor",
                        operation="echo",
                        resource="demo",
                        parameters={},
                    )
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
