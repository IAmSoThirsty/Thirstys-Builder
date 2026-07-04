"""LiveCluster: 3+ real HTTP nodes on the same host, voting over the wire.

This is the v0.3.0 reference for Volume VIII. Same-host (loopback HTTP)
but real inter-process communication: each node binds its own
`ThreadingHTTPServer`, accepts vote / heartbeat POSTs from peers, and
returns its local kernel's decision. `LiveCluster.submit(request)`
submits via any one node (the "entry" node), the entry node fans
out to peers, and the result is the same `ClusterDecision` shape as
the in-process `QuorumCluster`.

For multi-host, swap the `peers` URLs from `127.0.0.1:port` to the
real host:port (fronted with WireGuard or Tailscale for transport
security - no TLS in this implementation). The protocol is identical.
"""
from __future__ import annotations

import socket
import time
from dataclasses import dataclass
from typing import Any, Callable, Sequence

from ..audit import InMemoryAuditLog
from ..capability import CapabilityGrant, CapabilityRegistry
from ..cluster import ClusterDecision, FederationVerifier
from ..identity import IdentityRegistry, Subject
from ..kernel import ConstitutionalKernel
from ..models import ActionRequest, DecisionStatus
from ..policy import PolicyEffect, PolicyEngine, PolicyRule
from .node import FederationNode
from .protocol import HeartbeatBody, VoteBody
from .transport import (
    FederationClient,
    FederationError,
    FederationServer,
    PATH_ASK,
    fingerprint,
)


KernelFactory = Callable[[InMemoryAuditLog], ConstitutionalKernel]


def _free_port() -> int:
    """Bind to port 0, get the assigned port, close. Loopback only."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _make_default_kernel(*, allow: bool, audit_log: InMemoryAuditLog) -> ConstitutionalKernel:
    """A kernel with a single ALLOW or DENY rule, used in the conformance script."""
    return ConstitutionalKernel(
        identities=IdentityRegistry([Subject("operator", "Operator")]),
        policies=PolicyEngine(
            [
                PolicyRule(
                    "node-policy",
                    PolicyEffect.ALLOW if allow else PolicyEffect.DENY,
                    "echo",
                    "demo",
                    "operator",
                    "node allows" if allow else "node denies",
                )
            ]
        ),
        capabilities=(
            CapabilityRegistry([CapabilityGrant("grant", "operator", "echo", "demo")])
            if allow
            else CapabilityRegistry([])
        ),
        audit_log=audit_log,
        handlers={"echo": lambda resource, parameters: {"resource": resource, "parameters": parameters}},
    )


@dataclass
class _NodeSlot:
    node: FederationNode
    server: FederationServer
    base_url: str
    public_key: str


class LiveCluster:
    """A 3+ node federation with real HTTP between nodes.

    Each node runs on its own port on 127.0.0.1. The cluster holds a
    `partition_mask: set[node_id]`; nodes in the mask don't receive
    votes. The mask starts empty (no partition) and tests / ops
    toggle it to simulate network partitions.
    """

    def __init__(
        self,
        kernels: Sequence[ConstitutionalKernel],
        node_ids: Sequence[str] | None = None,
        public_keys: Sequence[str] | None = None,
    ) -> None:
        if len(kernels) < 1:
            raise ValueError("LiveCluster needs at least one node")
        n = len(kernels)
        ids = list(node_ids) if node_ids else [f"node-{i + 1}" for i in range(n)]
        if len(ids) != n:
            raise ValueError("node_ids length must match kernels length")
        keys = list(public_keys) if public_keys else [f"pubkey-{i}" for i in range(n)]
        if len(keys) != n:
            raise ValueError("public_keys length must match kernels length")

        self._slots: list[_NodeSlot] = []
        for i in range(n):
            port = _free_port()
            server = FederationServer(
                host="127.0.0.1",
                port=port,
                node_id=ids[i],
                public_key=keys[i],
            )
            # We attach the vote handler that runs the local kernel.
            # The handler is closure-bound to this slot's kernel.
            slot = _NodeSlot(
                node=None,  # filled in below
                server=server,
                base_url=f"http://127.0.0.1:{port}",
                public_key=keys[i],
            )
            server._on_ask = self._make_ask_handler(kernels[i], node_id=ids[i])  # type: ignore[attr-defined]
            server._on_heartbeat = self._make_heartbeat_handler()  # type: ignore[attr-defined]
            self._slots.append(slot)
            server.start()

        # Now build the FederationNodes with the peer topology.
        # Each node knows about all the others. The local node's own
        # decision is the first vote; peers are the rest.
        for i, slot in enumerate(self._slots):
            peers: list[tuple[str, str, str]] = []
            for j, other in enumerate(self._slots):
                if i == j:
                    continue
                peers.append((other.server.node_id, other.base_url, other.public_key))
            node = FederationNode(
                node_id=ids[i],
                public_key=keys[i],
                kernel=kernels[i],
                peers=tuple(peers),
                server=slot.server,
            )
            slot.node = node
            # Mark each peer as alive from the start (same-host = no warmup).
            for peer_id, _, _ in peers:
                node.record_peer_heartbeat(peer_id)

        self._partition_mask: set[str] = set()
        self._last_partition_change = time.monotonic()

    @property
    def nodes(self) -> tuple[FederationNode, ...]:
        return tuple(slot.node for slot in self._slots)

    def entry(self, index: int = 0) -> FederationNode:
        return self._slots[index].node

    # ---- partition simulation ----

    def set_partition(self, partitioned: set[str]) -> None:
        self._partition_mask = set(partitioned)
        self._last_partition_change = time.monotonic()
        # Each node's view of the cluster is the *full* partition set -
        # including itself if it is in the set. A node that is itself
        # partitioned cannot make decisions on behalf of the cluster,
        # because the cluster is "this set of nodes is gone." This is
        # the canonical split-brain guard: the entry node, if it is
        # in the partition set, must deny.
        for slot in self._slots:
            new_node = slot.node.with_partition(frozenset(self._partition_mask))
            slot.node = new_node

    def clear_partition(self) -> None:
        self.set_partition(set())

    @property
    def partition_mask(self) -> set[str]:
        return set(self._partition_mask)

    # ---- submission ----

    def submit(self, request: ActionRequest, entry_index: int = 0) -> ClusterDecision:
        return self.entry(entry_index).submit(request)

    def submit_via(self, request: ActionRequest, entry: FederationNode) -> ClusterDecision:
        return entry.submit(request)

    # ---- shutdown ----

    def stop(self) -> None:
        for slot in self._slots:
            slot.node.stop_heartbeats()
            slot.server.stop()

    # ---- internal handlers ----

    def _make_ask_handler(self, kernel: ConstitutionalKernel, node_id: str) -> Any:
        """Build a server-side handler: receive an ActionRequest, run the local
        kernel, return a VoteBody. The transport serializes it back to the
        caller as the response.
        """
        def handle(request: ActionRequest) -> "VoteBody":
            local = kernel.handle(request)
            events = getattr(kernel.audit_log, "events", None)
            event = None
            if events:
                event = next((e for e in reversed(events) if getattr(e, "request_id", None) == request.request_id), None)
            if event is None:
                # Mirror the in-process guarantee: a kernel that swallows the
                # request and emits no event is a bug. We fail closed.
                raise RuntimeError(f"kernel produced no audit event for {request.request_id}")
            from .protocol import VoteBody
            return VoteBody.from_decision(local, node_id, event)
        return handle

    def _make_heartbeat_handler(self) -> Any:
        from .protocol import HeartbeatBody as _HB
        def handle(hb: _HB) -> None:
            for node in self.nodes:
                if node.node_id != hb.node_id:
                    node.record_peer_heartbeat(hb.node_id)
        return handle


# ---------- convenience builders ----------


def build_live_cluster(
    *,
    node_count: int = 3,
    kernel_factory: KernelFactory | None = None,
    quorum: int | None = None,
) -> LiveCluster:
    """Build a 3-node (default) live cluster for testing and conformance.

    The default `kernel_factory` produces N kernels that all ALLOW the
    same operation. For chaos / partition tests, callers can pass a
    custom factory.
    """
    if node_count < 1:
        raise ValueError("node_count must be >= 1")
    if kernel_factory is None:
        kernels = [_make_default_kernel(allow=True, audit_log=InMemoryAuditLog()) for _ in range(node_count)]
    else:
        kernels = [kernel_factory(InMemoryAuditLog()) for _ in range(node_count)]
    cluster = LiveCluster(kernels)
    return cluster


def federation_hash_from_live(cluster: LiveCluster) -> str:
    """Compute the federation hash across all live nodes' audit logs.

    Same algorithm as `FederationVerifier._hash_events` - sorted by
    (node_id, event_id), SHA-256 of the canonical JSON.
    """
    from .protocol import policy_digest
    all_events: list[tuple[str, Any]] = []
    for node in cluster.nodes:
        for event in node.kernel.audit_log.events:
            all_events.append((node.node_id, event))
    canonical = [
        {
            "node_id": node_id,
            "event_id": event.event_id,
            "request_id": event.request_id,
            "event_hash": event.event_hash,
        }
        for node_id, event in sorted(all_events, key=lambda item: (item[0], item[1].event_id))
    ]
    import json
    import hashlib
    payload = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
