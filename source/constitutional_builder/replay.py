from __future__ import annotations

from dataclasses import dataclass

from .audit import AuditEvent, GENESIS_HASH, compute_event_hash


@dataclass(frozen=True)
class ReplayReport:
    valid: bool
    event_count: int
    reason: str


class ReplayVerifier:
    def verify(self, events: tuple[AuditEvent, ...]) -> ReplayReport:
        previous_hash = GENESIS_HASH
        for index, event in enumerate(events, start=1):
            if event.previous_hash != previous_hash:
                return ReplayReport(False, index, "previous hash mismatch")
            if compute_event_hash(event.__dict__) != event.event_hash:
                return ReplayReport(False, index, "event hash mismatch")
            previous_hash = event.event_hash
        return ReplayReport(True, len(events), "audit chain verified")
