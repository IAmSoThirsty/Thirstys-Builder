"""Federation sub-package: live, multi-process quorum over HTTP.

Re-exports the protocol types from `.protocol` and the live cluster
machinery from `.cluster_live` and `.node` and `.transport`.
"""
from .cluster_live import (
    LiveCluster,
    build_live_cluster,
    federation_hash_from_live,
)
from .node import FederationNode
from .protocol import (
    Attestation,
    FederationMessage,
    HeartbeatBody,
    MessageKind,
    PROTOCOL_VERSION,
    VoteBody,
    b64,
    b64d,
    policy_digest,
)
from .transport import (
    FederationClient,
    FederationError,
    FederationServer,
    PATH_ASK,
    PATH_HEARTBEAT,
    PATH_INFO,
    fingerprint,
)

__all__ = [
    "Attestation",
    "FederationClient",
    "FederationError",
    "FederationMessage",
    "FederationNode",
    "FederationServer",
    "HeartbeatBody",
    "LiveCluster",
    "MessageKind",
    "PATH_ASK",
    "PATH_HEARTBEAT",
    "PATH_INFO",
    "PROTOCOL_VERSION",
    "VoteBody",
    "b64",
    "b64d",
    "build_live_cluster",
    "federation_hash_from_live",
    "fingerprint",
    "policy_digest",
]
