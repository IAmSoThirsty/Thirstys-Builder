# Federation - Volume VIII

This is the live multi-host consensus path for the Constitutional
Builder. v0.3.0 ships the wire protocol, the same-host multi-process
reference implementation, and the partition-recovery semantics.
Multi-host (separate machines) uses the same protocol with
`127.0.0.1` swapped for the peer's real address, fronted with
WireGuard or Tailscale for transport security (no TLS in this
implementation - by design, the loopback-only rule keeps TLS out
of the trust model).

## Why this exists

The in-process `QuorumCluster` (Volume VIII conformance) proves the
quorum math: 2 of 3 nodes can allow, 1 of 3 cannot, and so on. The
*live* `LiveCluster` proves the same math holds when the nodes are
separate processes communicating over HTTP. The two paths answer
different questions:

- `QuorumCluster` (in-process): "is the math right?" (CI-fast, deterministic)
- `LiveCluster` (multi-process): "does the math hold over a real wire?" (CI slower, exercises transport)

The roadmap line for this is:

> 0.2.0 - Multi-host consensus (CBEP volume 8) - actual federation, not just the conformance check

That `not just the conformance check` is the difference between
`QuorumCluster` (conformance) and `LiveCluster` (actual federation).
v0.3.0 closes that line.

## Wire protocol

`federation-v1`. JSON over HTTP. Loopback-only by default.

| Endpoint | Method | Body | Response |
|----------|--------|------|----------|
| `/federation/v1/info` | GET | - | `{version, node_id, public_key}` |
| `/federation/v1/ask` | POST | `{kind: "ask", body: <ActionRequest dict>}` | `{vote: <VoteBody dict>}` |
| `/federation/v1/heartbeat` | POST | `{kind: "heartbeat", body: <HeartbeatBody dict>}` | `{ok: true}` |

All POSTs require `Authorization: Bearer <sha256(public_key)[:16] hex>`.
The server checks the bearer against the configured public key
fingerprint and rejects the request with 403 if they don't match.

### Message kinds

- `ask`: "please run this ActionRequest against your local kernel and
  return your vote." Used by the entry node to fan out to peers.
- `heartbeat`: liveness + drift detection. Sent every
  `heartbeat_interval_seconds` (default 1s). Includes the node's
  `policy_digest` (a SHA-256 of the rules in its `PolicyEngine`).
  If a peer's digest doesn't match the local node's digest, the
  peer is refusing to vote (drift detection is an open hook in
  v0.3.0 - the drift refusal path is not yet enforced; the digest
  is computed and sent, but nodes don't reject drift peers yet).
- `policy_digest_mismatch`: reserved for the drift refusal path
  (not yet emitted by any code).

### Quorum semantics

The quorum bar is the **configured cluster size**, not the live
view. With 5 nodes, quorum is 3 (`(5 // 2) + 1`). If a node can
only see 2 of its 4 peers, the visible count is 3 (itself + 2
peers), which equals the configured quorum. If a node can only see
1 of its 4 peers, the visible count is 2, which is less than the
configured quorum - the request is denied with
`cluster partition - quorum unreachable`.

This is the canonical split-brain guard. A node that has lost
contact with quorum-many peers cannot make decisions on behalf of
the cluster, even if its own local decision would have allowed.
This is the same property Raft and Paxos enforce, implemented
here in a way that doesn't require a leader.

### Vote recording

A vote is the peer's local decision. The peer runs its own
`ConstitutionalKernel.handle(request)` and returns a `VoteBody`
containing the `Decision` (status, reason, audit_event_id) and the
full `AuditEvent`. The entry node tallies the votes and emits a
`ClusterDecision` with the same shape as the in-process one.

## Same-host usage

```python
from constitutional_builder import build_live_cluster, ActionRequest

cluster = build_live_cluster(node_count=3)  # 3 HTTP servers on loopback
decision = cluster.submit(ActionRequest("r1", "operator", "echo", "demo", {}))
print(decision.status.value)  # "allowed"
print(decision.approvals, "/", decision.quorum)

# Partition simulation: drop a peer
cluster.set_partition({"node-3"})
decision = cluster.submit(ActionRequest("r2", "operator", "echo", "demo", {}))
print(decision.status.value)  # "allowed" (2 of 3 still meet quorum)

# Two-peer partition: split-brain
cluster.set_partition({"node-2", "node-3"})
decision = cluster.submit(ActionRequest("r3", "operator", "echo", "demo", {}))
print(decision.status.value)  # "denied" - reason: cluster partition - quorum unreachable

# Recover
cluster.clear_partition()
decision = cluster.submit(ActionRequest("r4", "operator", "echo", "demo", {}))
print(decision.status.value)  # "allowed"

cluster.stop()
```

## Multi-host deployment

The protocol is the same. The only difference is the peer URLs.

### WireGuard overlay (recommended)

1. Set up WireGuard on each host. Use the existing
   `thirsty-ai-builder/deploy/ollama-wireguard.conf.example` as a
   template for the Ollama side; mirror it for the federation side.
2. Bind each node's `FederationServer` to the WireGuard overlay IP
   instead of `127.0.0.1`. The constructor currently rejects
   non-loopback hosts; pass a sentinel that maps to a real
   interface, or extend the constructor to accept a "trusted
   transport" flag that whitelists an overlay subnet. (The latter
   is the right path - see "Open work" below.)
3. The cluster config is a list of `(node_id, http://10.42.0.X:8001, public_key)` tuples.
4. The same `LiveCluster` code path runs unchanged. The only
   difference is each `FederationClient` is talking to a different
   machine over a WireGuard tunnel.

### TLS

The reference implementation has no TLS. The threat model is:
WireGuard / Tailscale provides the encrypted transport; the
federation protocol is on top of an authenticated overlay. Adding
TLS to the federation server would mean a second layer of mutual
auth, which the design does not need (the overlay already provides
mutual auth via the public keys in the WireGuard config).

If you need TLS without an overlay: front the federation server
with a reverse proxy (Caddy, nginx) and use that as the peer URL.
The protocol stays the same.

## Open work (not in v0.3.0)

- **Drift refusal enforcement.** `policy_digest` is computed and
  sent in every heartbeat, but a node does not yet refuse votes
  from a peer whose digest differs. The hook is in place
  (`MessageKind.POLICY_DIGEST_MISMATCH`); wiring the check is
  mechanical.
- **Multi-host release artifact.** The same-host test runs on every
  CI. A multi-host test would need at least 2 machines; the protocol
  is identical.
- **Persistent peer list.** Currently the peer list is passed in at
  construction. A persistent peer registry (config file, Consul,
  etcd) is the next layer.

## Test matrix

`tests/test_live_federation.py` covers:

| Test | What it proves |
|------|----------------|
| `test_baseline_all_nodes_allow` | 3/3 happy path |
| `test_one_node_denies_quorum_still_reached` | 2 allow / 1 deny still meets quorum |
| `test_single_node_partition_still_quorum` | 1 peer dropped, 2/2 visible, allow |
| `test_two_node_partition_split_brain_denies` | 2 peers dropped, visible=1 < quorum=2, deny |
| `test_clear_partition_recovers` | clear partition, full quorum restored |
| `test_quorum_uses_configured_not_visible` | 5-node boundary, visible=3=quorum, allow |
| `test_federation_hash_is_deterministic` | hash is a valid SHA-256 |
| `test_federation_verifier_accepts_live_cluster` | in-process verifier reads live audit logs |
| `test_federation_message_round_trip` | wire serialization |
| `test_federation_message_version_mismatch_rejected` | bad version is rejected |
| `test_fingerprint_deterministic` | bearer is reproducible |
| `test_policy_digest_changes_with_rules` | digest is a real drift detector |
| `test_vote_body_round_trip` | vote serialization |
| `test_server_rejects_non_loopback` | non-loopback bind is refused |
| `test_info_endpoint` | info endpoint returns version+identity |

`scripts/run_live_federation_conformance.py` runs the 6-step
end-to-end scenario used by the CBEP gate. Step 16 of
`scripts/verify_all.py`.
