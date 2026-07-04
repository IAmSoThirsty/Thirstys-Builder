"""FederationNode: a ConstitutionalKernel with a peer set and outbound vote client.

A `FederationNode` is the local side of the federation protocol. It
holds:

- A `ConstitutionalKernel` (the local authority).
- A list of peer `FederationClient`s.
- A node identity (`node_id` + `public_key`).
- A partition mask: peers in the mask don't get called. Used by tests
  to simulate network partitions. In production, the partition mask
  is derived from heartbeat-based liveness.

`submit(request)` does the local kernel decision, fans the request
out to peers, gathers votes, and returns a `ClusterDecision` with
the same shape as the in-process `QuorumCluster.ClusterDecision`.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any

from ..audit import AuditEvent
from ..cluster import ClusterDecision
from ..kernel import ConstitutionalKernel
from ..models import ActionRequest, DecisionStatus
from .protocol import (
    HeartbeatBody,
    MessageKind,
    VoteBody,
    policy_digest,
)
from .transport import FederationClient, FederationError, FederationServer, fingerprint


@dataclass(frozen=True)
class FederationNode:
    """One node in a live federation.

    `peers` is a list of (node_id, base_url, public_key) tuples. The
    node's own public_key is NOT in peers (it doesn't vote for its
    own requests to itself, but it does count its own local decision
    in the quorum tally).
    """

    node_id: str
    public_key: str
    kernel: ConstitutionalKernel
    peers: tuple[tuple[str, str, str], ...]   # (node_id, base_url, public_key)
    server: FederationServer | None = None
    heartbeat_interval_seconds: float = 1.0
    heartbeat_timeout_seconds: float = 5.0
    vote_timeout_seconds: float = 2.0
    _partition_mask: frozenset[str] = field(default_factory=frozenset, repr=False, compare=False)
    _peers_lock: threading.Lock = field(default_factory=threading.Lock, repr=False, compare=False)
    _peers_seen: dict[str, float] = field(default_factory=dict, repr=False, compare=False)
    _hb_thread: threading.Thread | None = field(default=None, repr=False, compare=False)
    _hb_stop: threading.Event = field(default_factory=threading.Event, repr=False, compare=False)

    # ---- peer management ----

    def with_partition(self, partitioned: frozenset[str]) -> "FederationNode":
        """Return a copy of this node with a new partition mask. Used in tests.

        Preserves the `_peers_seen` map (liveness state) and the partition
        timeout config across the copy. The `_partition_mask` is the only
        field that changes - and it is the only one callers care about.
        """
        new = FederationNode(
            node_id=self.node_id,
            public_key=self.public_key,
            kernel=self.kernel,
            peers=self.peers,
            server=self.server,
            heartbeat_interval_seconds=self.heartbeat_interval_seconds,
            heartbeat_timeout_seconds=self.heartbeat_timeout_seconds,
            vote_timeout_seconds=self.vote_timeout_seconds,
            _partition_mask=partitioned,
            _peers_seen=dict(self._peers_seen),
        )
        return new

    def record_peer_heartbeat(self, peer_node_id: str) -> None:
        with self._peers_lock:
            self._peers_seen[peer_node_id] = time.monotonic()

    def peer_alive(self, peer_node_id: str) -> bool:
        with self._peers_lock:
            last = self._peers_seen.get(peer_node_id)
            if last is None:
                return False
            return (time.monotonic() - last) < self.heartbeat_timeout_seconds

    # ---- submission ----

    def submit(self, request: ActionRequest) -> ClusterDecision:
        """Submit a request to this node's cluster.

        1. Run the local kernel: that's the local decision and one of the votes.
        2. POST the request to each un-partitioned peer. Each peer runs its own
           kernel locally and returns a VoteBody.
        3. Tally approvals vs denials. The quorum bar is the *configured*
           cluster size, not the visible size. If the local node can't see
           enough peers to meet quorum (because of a partition, *including*
           the entry being partitioned), the request is denied with reason
           "cluster partition - quorum unreachable". This is the canonical
           split-brain guard: a node that has lost contact with quorum-many
           peers cannot make decisions on behalf of the cluster, even if
           its own local decision would have allowed.
        4. The local decision counts toward the tally *only if* this node
           is not itself partitioned. A partitioned entry node's own vote
           is dropped, on the same logic as a peer's vote: a dead node's
           vote is a dead vote.
        """
        request.validate()
        configured_quorum = (len(self.peers) + 1) // 2 + 1
        entry_partitioned = self.node_id in self._partition_mask

        local_decision = self.kernel.handle(request)
        local_event = self._last_event_for(request.request_id)
        if local_event is None:
            raise RuntimeError("local kernel produced no audit event for the request")

        approvals = 0
        denials = 0
        node_decisions: list[Any] = []
        node_events: list[tuple[str, Any]] = []

        if not entry_partitioned:
            if local_decision.allowed:
                approvals += 1
            else:
                denials += 1
            node_decisions.append(local_decision)
            node_events.append((self.node_id, local_event))

        for peer_id, peer_url, peer_pk in self.peers:
            if peer_id in self._partition_mask or not self.peer_alive(peer_id):
                continue
            client = FederationClient(peer_url, bearer=fingerprint(peer_pk), timeout_seconds=self.vote_timeout_seconds)
            try:
                vote_dict = client.post_ask(request)
                vote = VoteBody.from_dict(vote_dict)
            except FederationError as exc:
                # A failed peer call counts as a denial (we never got a vote
                # and we don't fabricate one). The cluster keeps the local
                # decision and the rest of the live votes.
                continue
            node_decisions.append(vote.to_decision())
            node_events.append((peer_id, _event_from_dict(vote.audit_event)))
            if vote.status == DecisionStatus.ALLOWED.value:
                approvals += 1
            else:
                denials += 1

        # Visible cluster size = us + peers we got a vote from. If this is
        # less than the configured quorum, we cannot honor the cluster's
        # decision - we are in a partition. Fail closed.
        visible = 1 + sum(
            1 for n in node_decisions[1:]
        )
        if visible < configured_quorum:
            return ClusterDecision(
                request_id=request.request_id,
                status=DecisionStatus.DENIED,
                reason=f"cluster partition - quorum unreachable (visible={visible}, configured={configured_quorum})",
                quorum=configured_quorum,
                approvals=approvals,
                denials=denials,
                node_decisions=tuple(node_decisions),
            )

        if approvals >= configured_quorum:
            return ClusterDecision(
                request_id=request.request_id,
                status=DecisionStatus.ALLOWED,
                reason="cluster quorum allowed",
                quorum=configured_quorum,
                approvals=approvals,
                denials=denials,
                node_decisions=tuple(node_decisions),
            )
        return ClusterDecision(
            request_id=request.request_id,
            status=DecisionStatus.DENIED,
            reason="cluster quorum not reached",
            quorum=configured_quorum,
            approvals=approvals,
            denials=denials,
            node_decisions=tuple(node_decisions),
        )

    def _quorum_size(self) -> int:
        """The local view of the cluster size: 1 (us) + live peers."""
        live = sum(1 for pid, _, _ in self.peers if pid not in self._partition_mask and self.peer_alive(pid))
        return (live + 1) // 2 + 1  # majority of (us + live peers)

    def respond_to_request(self, request: ActionRequest) -> VoteBody:
        """The peer's side: run the local kernel, return a vote body."""
        request.validate()
        local = self.kernel.handle(request)
        event = self._last_event_for(request.request_id)
        if event is None:
            raise RuntimeError("peer kernel produced no audit event for the request")
        return VoteBody.from_decision(local, self.node_id, event)

    def _last_event_for(self, request_id: str) -> Any:
        # AuditLog.append returns the new event; we just want the most recent
        # event whose request_id matches. The InMemoryAuditLog preserves order.
        log = self.kernel.audit_log
        events = getattr(log, "events", None)
        if events is None:
            return None
        for event in reversed(events):
            if getattr(event, "request_id", None) == request_id:
                return event
        return None

    # ---- heartbeat ----

    def start_heartbeats(self) -> None:
        if self._hb_thread is not None:
            return
        self._hb_stop.clear()
        self._hb_thread = threading.Thread(
            target=self._heartbeat_loop, name=f"federation-hb-{self.node_id}", daemon=True
        )
        self._hb_thread.start()

    def stop_heartbeats(self) -> None:
        self._hb_stop.set()
        if self._hb_thread is not None:
            self._hb_thread.join(timeout=3.0)
            self._hb_thread = None

    def _heartbeat_loop(self) -> None:
        while not self._hb_stop.is_set():
            digest = policy_digest(self.kernel.policies)
            last_event = ""
            events = getattr(self.kernel.audit_log, "events", None)
            if events:
                last_event = getattr(events[-1], "event_id", "") or ""
            hb = HeartbeatBody(
                node_id=self.node_id,
                policy_digest=digest,
                last_event_id=last_event,
                timestamp=time.time(),
            )
            for peer_id, peer_url, peer_pk in self.peers:
                if peer_id in self._partition_mask:
                    continue
                client = FederationClient(
                    peer_url, bearer=fingerprint(peer_pk), timeout_seconds=self.vote_timeout_seconds
                )
                try:
                    client.post_heartbeat(hb)
                except FederationError:
                    pass  # liveness will catch it
            self._hb_stop.wait(self.heartbeat_interval_seconds)

from ..audit import AuditEvent
def _event_from_dict(d: dict[str, Any]) -> AuditEvent:
    return AuditEvent(**d)
