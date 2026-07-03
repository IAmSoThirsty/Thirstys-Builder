from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from .audit import AuditEvent, InMemoryAuditLog
from .kernel import ConstitutionalKernel
from .models import ActionRequest, Decision, DecisionStatus
from .replay import ReplayVerifier


@dataclass(frozen=True)
class BuilderNode:
    node_id: str
    kernel: ConstitutionalKernel

    def handle(self, request: ActionRequest) -> Decision:
        return self.kernel.handle(request)


@dataclass(frozen=True)
class ClusterDecision:
    request_id: str
    status: DecisionStatus
    reason: str
    quorum: int
    approvals: int
    denials: int
    node_decisions: tuple[Decision, ...]

    @property
    def allowed(self) -> bool:
        return self.status is DecisionStatus.ALLOWED


class QuorumCluster:
    def __init__(self, nodes: list[BuilderNode], quorum: int | None = None) -> None:
        if not nodes:
            raise ValueError("cluster requires at least one node")
        self.nodes = tuple(nodes)
        self.quorum = quorum if quorum is not None else (len(nodes) // 2) + 1
        if self.quorum < 1 or self.quorum > len(nodes):
            raise ValueError("quorum must be between 1 and node count")

    def submit(self, request: ActionRequest) -> ClusterDecision:
        decisions = tuple(node.handle(request) for node in self.nodes)
        approvals = sum(1 for decision in decisions if decision.allowed)
        denials = len(decisions) - approvals
        if approvals >= self.quorum:
            return ClusterDecision(
                request_id=request.request_id,
                status=DecisionStatus.ALLOWED,
                reason="cluster quorum allowed",
                quorum=self.quorum,
                approvals=approvals,
                denials=denials,
                node_decisions=decisions,
            )
        return ClusterDecision(
            request_id=request.request_id,
            status=DecisionStatus.DENIED,
            reason="cluster quorum not reached",
            quorum=self.quorum,
            approvals=approvals,
            denials=denials,
            node_decisions=decisions,
        )


@dataclass(frozen=True)
class FederationReport:
    valid: bool
    event_count: int
    federation_hash: str
    reason: str


class FederationVerifier:
    def verify(self, nodes: tuple[BuilderNode, ...]) -> FederationReport:
        replay = ReplayVerifier()
        all_events: list[tuple[str, AuditEvent]] = []
        for node in nodes:
            report = replay.verify(node.kernel.audit_log.events)
            if not report.valid:
                return FederationReport(False, report.event_count, "", f"{node.node_id}: {report.reason}")
            for event in node.kernel.audit_log.events:
                all_events.append((node.node_id, event))

        federation_hash = self._hash_events(all_events)
        return FederationReport(True, len(all_events), federation_hash, "federation audit verified")

    @staticmethod
    def _hash_events(events: list[tuple[str, AuditEvent]]) -> str:
        canonical = [
            {
                "node_id": node_id,
                "event_id": event.event_id,
                "request_id": event.request_id,
                "event_hash": event.event_hash,
            }
            for node_id, event in sorted(events, key=lambda item: (item[0], item[1].event_id))
        ]
        payload = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_cluster(
    *,
    node_count: int,
    kernel_factory,
    quorum: int | None = None,
) -> QuorumCluster:
    nodes = [
        BuilderNode(f"node-{index + 1}", kernel_factory(audit_log=InMemoryAuditLog()))
        for index in range(node_count)
    ]
    return QuorumCluster(nodes, quorum=quorum)
