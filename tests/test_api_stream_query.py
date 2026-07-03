import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.request import urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "source"))

from constitutional_builder.api import make_server  # noqa: E402
from constitutional_builder.config import build_kernel_from_config, load_config  # noqa: E402


class ApiStreamQueryTests(unittest.TestCase):
    def test_audit_stream_returns_sse_events(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "subjects": [{"subject_id": "operator", "display_name": "Operator"}],
                        "policies": [
                            {
                                "policy_id": "allow",
                                "effect": "allow",
                                "subject_id": "operator",
                                "operation": "echo",
                                "resource": "demo",
                            }
                        ],
                        "capabilities": [
                            {
                                "grant_id": "grant",
                                "subject_id": "operator",
                                "operation": "echo",
                                "resource": "demo",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            kernel = build_kernel_from_config(load_config(config_path))
            server = make_server(kernel, "127.0.0.1", 0)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                host, port = server.server_address
                base = f"http://{host}:{port}"
                request = json.dumps(
                    {
                        "request_id": "req-1",
                        "subject_id": "operator",
                        "operation": "echo",
                        "resource": "demo",
                        "parameters": {},
                    }
                ).encode("utf-8")
                execute = urlopen(
                    url=f"{base}/v1/execute",
                    data=request,
                    timeout=5,
                )
                self.assertEqual(execute.status, 200)

                stream = urlopen(f"{base}/v1/audit/stream", timeout=5)
                body = stream.read().decode("utf-8")
                self.assertIn("event: audit", body)
                self.assertIn('"request_id": "req-1"', body)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
