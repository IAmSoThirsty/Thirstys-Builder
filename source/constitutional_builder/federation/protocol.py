"""Federation protocol types - Volume VIII (Distributed Builder Federation).

Wire format: JSON over HTTP, version 1. Every cross-node message is
signed by the sender's Ed25519 key (CBEP-003 attestation). The receiver
re-checks the signature against its known peer list before processing.

This file is transport-agnostic: only data types, no HTTP, no sockets.
`federation/transport.py` implements the HTTP layer.
"""
from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

from ..audit import AuditEvent
from ..models import ActionRequest, Decision, DecisionStatus

# Protocol version. Bump on a breaking change to the wire format.
PROTOCOL_VERSION = "federation-v1"


class MessageKind(str, Enum):
    """Wire-level message kinds."""

    ASK = "ask"                  # "please vote on this request"
    HEARTBEAT = "heartbeat"      # liveness + policy digest
    POLICY_DIGEST_MISMATCH = "policy_digest_mismatch"  # peer drift refusal


@dataclass(frozen=True)
class Attestation:
    """CBEP-003 attestation envelope.

    Every wire message carries an attestation that the receiver can
    verify independently. The signature is over the canonical
    serialization of (sender, payload) - a header parameter to keep
    the canonical form simple and version-pinned.
    """

    sender: str             # node_id of the sender
    public_key: str         # base64 Ed25519 public key
    payload: str            # base64 of the canonical JSON body
    signature: str          # base64 Ed25519 signature over (sender + payload)

    def to_dict(self) -> dict[str, str]:
        return {
            "sender": self.sender,
            "public_key": self.public_key,
            "payload": self.payload,
            "signature": self.signature,
        }

    @staticmethod
    def from_dict(d: dict[str, str]) -> "Attestation":
        return Attestation(
            sender=d["sender"],
            public_key=d["public_key"],
            payload=d["payload"],
            signature=d["signature"],
        )


@dataclass(frozen=True)
class FederationMessage:
    """A single wire message - one Attestation wrapping one body."""

    kind: MessageKind
    body: dict[str, Any]
    attestation: Attestation | None = None  # signed messages carry one
    policy_digest: str | None = None  # sender's local policy digest, for drift refusal
    sender_node_id: str | None = None  # sender's node_id, for server-side bookkeeping

    def to_json(self) -> str:
        d: dict[str, Any] = {"version": PROTOCOL_VERSION, "kind": self.kind.value, "body": self.body}
        if self.attestation is not None:
            d["attestation"] = self.attestation.to_dict()
        if self.policy_digest is not None:
            d["policy_digest"] = self.policy_digest
        if self.sender_node_id is not None:
            d["sender_node_id"] = self.sender_node_id
        return json.dumps(d, sort_keys=True, separators=(",", ":"))

    @staticmethod
    def from_json(text: str) -> "FederationMessage":
        d = json.loads(text)
        if d.get("version") != PROTOCOL_VERSION:
            raise ValueError(f"unsupported protocol version: {d.get('version')!r}")
        att = d.get("attestation")
        return FederationMessage(
            kind=MessageKind(d["kind"]),
            body=d["body"],
            attestation=Attestation.from_dict(att) if att else None,
            policy_digest=d.get("policy_digest"),
            sender_node_id=d.get("sender_node_id"),
        )


@dataclass(frozen=True)
class VoteBody:
    """A node's local decision on a request.

    Mirrors `constitutional_builder.models.Decision` but flattened
    for the wire: the audit_event_id and reason travel as plain
    strings; the request_id is duplicated to make audit merging
    trivial on the receiving side.
    """

    request_id: str
    node_id: str
    status: str              # DecisionStatus.value
    reason: str
    audit_event_id: str
    audit_event: dict[str, Any]   # full event for replay

    @staticmethod
    def from_decision(decision: Decision, node_id: str, event: AuditEvent) -> "VoteBody":
        return VoteBody(
            request_id=decision.request_id,
            node_id=node_id,
            status=decision.status.value,
            reason=decision.reason,
            audit_event_id=decision.audit_event_id,
            audit_event=_event_to_dict(event),
        )

    def to_decision(self) -> Decision:
        return Decision(
            request_id=self.request_id,
            status=DecisionStatus(self.status),
            reason=self.reason,
            audit_event_id=self.audit_event_id,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "node_id": self.node_id,
            "status": self.status,
            "reason": self.reason,
            "audit_event_id": self.audit_event_id,
            "audit_event": self.audit_event,
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "VoteBody":
        return VoteBody(
            request_id=d["request_id"],
            node_id=d["node_id"],
            status=d["status"],
            reason=d["reason"],
            audit_event_id=d["audit_event_id"],
            audit_event=d["audit_event"],
        )


@dataclass(frozen=True)
class HeartbeatBody:
    """Liveness + drift detection.

    A node sends a heartbeat every `heartbeat_interval_seconds`. The
    payload includes the node's policy digest (a hash of its current
    PolicyBundle / PolicyEngine). If a peer's digest drifts from the
    local node's digest, the local node refuses its votes until
    reconciliation (out of scope for v0.2.1).
    """

    node_id: str
    policy_digest: str
    last_event_id: str
    timestamp: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "policy_digest": self.policy_digest,
            "last_event_id": self.last_event_id,
            "timestamp": self.timestamp,
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "HeartbeatBody":
        return HeartbeatBody(
            node_id=d["node_id"],
            policy_digest=d["policy_digest"],
            last_event_id=d["last_event_id"],
            timestamp=d["timestamp"],
        )


# ---------- helpers ----------


def _event_to_dict(event: AuditEvent) -> dict[str, Any]:
    """Canonical dict of an AuditEvent for wire transport."""
    return asdict(event)


def policy_digest(policy_engine: Any) -> str:
    """Stable SHA-256 of a PolicyEngine's rules.

    A PolicyEngine has a list of PolicyRule objects with a stable
    to_dict() shape; we canonicalize with sort_keys and hash the
    result. Same policy -> same digest, byte-for-byte. This is the
    wire-level drift detector: a node whose digest doesn't match the
    cluster's is refusing to vote (the kernel enforces local
    authorization can't be weakened by a peer).
    """
    # PolicyEngine stores its rules as a private `_rules` tuple.
    rules_attr = getattr(policy_engine, "_rules", None) or getattr(policy_engine, "rules", None)
    if rules_attr is None:
        raise TypeError(f"policy_engine has no rules: {policy_engine!r}")
    rules = [r.to_dict() if hasattr(r, "to_dict") else asdict(r) for r in rules_attr]
    canonical = json.dumps(rules, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def b64(data: bytes) -> str:
    return base64.standard_b64encode(data).decode("ascii")


def b64d(text: str) -> bytes:
    return base64.standard_b64decode(text.encode("ascii"))
