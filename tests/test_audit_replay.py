import sys
import unittest
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "source"))

from constitutional_builder.audit import InMemoryAuditLog  # noqa: E402
from constitutional_builder.replay import ReplayVerifier  # noqa: E402


class AuditReplayTests(unittest.TestCase):
    def test_tampered_event_fails_replay(self):
        audit = InMemoryAuditLog()
        event = audit.append(
            request_id="req-1",
            subject_id="alice",
            operation="echo",
            resource="resource",
            status="allowed",
            reason="test",
            metadata={"ok": True},
        )

        tampered = replace(event, reason="changed after append")
        report = ReplayVerifier().verify((tampered,))

        self.assertFalse(report.valid)
        self.assertEqual(report.reason, "event hash mismatch")


if __name__ == "__main__":
    unittest.main()
