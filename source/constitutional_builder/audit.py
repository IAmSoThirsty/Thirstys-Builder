from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


GENESIS_HASH = "0" * 64


@dataclass(frozen=True)
class AuditEvent:
    event_id: str
    request_id: str
    subject_id: str
    operation: str
    resource: str
    status: str
    reason: str
    timestamp: str
    previous_hash: str
    event_hash: str
    metadata: dict[str, Any]


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def compute_event_hash(payload: dict[str, Any]) -> str:
    event_payload = {key: value for key, value in payload.items() if key != "event_hash"}
    return hashlib.sha256(_canonical_json(event_payload).encode("utf-8")).hexdigest()


class InMemoryAuditLog:
    def __init__(self) -> None:
        self._events: list[AuditEvent] = []

    @property
    def events(self) -> tuple[AuditEvent, ...]:
        return tuple(self._events)

    def append(
        self,
        *,
        request_id: str,
        subject_id: str,
        operation: str,
        resource: str,
        status: str,
        reason: str,
        metadata: dict[str, Any] | None = None,
    ) -> AuditEvent:
        previous_hash = self._events[-1].event_hash if self._events else GENESIS_HASH
        event_id = f"evt-{len(self._events) + 1:08d}"
        payload: dict[str, Any] = {
            "event_id": event_id,
            "request_id": request_id,
            "subject_id": subject_id,
            "operation": operation,
            "resource": resource,
            "status": status,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "previous_hash": previous_hash,
            "event_hash": "",
            "metadata": metadata or {},
        }
        payload["event_hash"] = compute_event_hash(payload)
        event = AuditEvent(**payload)
        self._events.append(event)
        return event

    def verify(self) -> bool:
        previous_hash = GENESIS_HASH
        for event in self._events:
            payload = asdict(event)
            if event.previous_hash != previous_hash:
                return False
            if compute_event_hash(payload) != event.event_hash:
                return False
            previous_hash = event.event_hash
        return True


class FileAuditLog(InMemoryAuditLog):
    def __init__(self, path: str | Path) -> None:
        super().__init__()
        self.path = Path(path)
        if self.path.exists():
            self._events.extend(self._read_events(self.path))

    def append(self, **kwargs: Any) -> AuditEvent:
        event = super().append(**kwargs)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(_canonical_json(asdict(event)) + "\n")
        return event

    @staticmethod
    def _read_events(path: Path) -> Iterable[AuditEvent]:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    yield AuditEvent(**json.loads(line))
