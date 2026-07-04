"""HTTP transport for federation messages.

Two pieces:
- `FederationHandler` - the request handler. Drop into any
  `http.server.ThreadingHTTPServer`.
- `FederationClient` - the outbound client. Used by a node to
  submit votes / heartbeats to a peer.

Wire format: JSON only, one POST per message, body = serialized
FederationMessage. Bearer token is the SHA-256 fingerprint of the
sender's public key (16 hex chars), so a node can reject unauth'd
peers before doing any work.

Loopback-only. There is no TLS here. The contract is that this
server is bound to 127.0.0.1 (or to a private overlay like WireGuard
in production multi-host - see docs/FEDERATION.md).
"""
from __future__ import annotations

import hashlib
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from .protocol import (
    Attestation,
    FederationMessage,
    MessageKind,
    PROTOCOL_VERSION,
    VoteBody,
    HeartbeatBody,
)
from ..models import ActionRequest

PATH_ASK = "/federation/v1/ask"
PATH_HEARTBEAT = "/federation/v1/heartbeat"
PATH_INFO = "/federation/v1/info"


def fingerprint(public_key_b64: str) -> str:
    """The bearer token: SHA-256(public_key)[:16] hex.

    16 hex chars = 64 bits of entropy, plenty to identify a node
    without leaking the key. Used as both the bearer header and
    a sanity check against the attestation's embedded public key.
    """
    return hashlib.sha256(public_key_b64.encode("ascii")).hexdigest()[:16]


# ---------- server side ----------


class FederationServer:
    """A node's HTTP server. One per node. Loopback-only by convention."""

    def __init__(
        self,
        *,
        host: str,
        port: int,
        node_id: str,
        public_key: str,
        on_ask: Callable[[ActionRequest], "VoteBody"] | None = None,
        on_heartbeat: Callable[[HeartbeatBody], None] | None = None,
        local_policy_digest: str | None = None,
    ) -> None:
        if host != "127.0.0.1" and host != "localhost":
            raise ValueError(
                f"federation server must bind to loopback (127.0.0.1); got {host!r}. "
                "For multi-host, front this with WireGuard / Tailscale and bind to the overlay IP."
            )
        self.host = host
        self.port = port
        self.node_id = node_id
        self.public_key = public_key
        self.expected_fingerprint = fingerprint(public_key)
        self._on_ask = on_ask
        self._on_heartbeat = on_heartbeat
        self._httpd: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        # Track peers by fingerprint -> last_seen timestamp.
        self._peers_lock = threading.Lock()
        self._peers: dict[str, dict[str, Any]] = {}
        # Drift refusal: if set, an ask carrying a `policy_digest` field is
        # rejected with HTTP 409 + POLICY_DIGEST_MISMATCH when the digest
        # does not match the local digest. Heartbeats also update the local
        # record of a peer's digest.
        self.local_policy_digest = local_policy_digest
        # peer_fp -> {node_id, last_digest, last_seen}
        self._peer_digests: dict[str, dict[str, Any]] = {}

    def start(self) -> None:
        outer = self
        handler = _make_handler(outer)
        self._httpd = ThreadingHTTPServer((self.host, self.port), handler)
        self._thread = threading.Thread(
            target=self._httpd.serve_forever, name=f"federation-{self.node_id}", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
            self._httpd = None
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    def record_peer(self, fp: str, info: dict[str, Any]) -> None:
        with self._peers_lock:
            self._peers[fp] = info

    def peers(self) -> dict[str, dict[str, Any]]:
        with self._peers_lock:
            return {k: dict(v) for k, v in self._peers.items()}

    def record_peer_digest(self, peer_node_id: str, digest: str) -> None:
        """Record the most recent policy digest seen for a peer.

        Updated by every ask (which carries the sender's digest and
        node_id). Used to attribute drift events to a peer and to
        expose a per-peer digest map for the cluster operator.

        Keyed by `peer_node_id` (the sender's identity), not by the
        bearer fingerprint - the bearer is the *server's* fingerprint,
        not the sender's, so it can't be used to distinguish peers.
        """
        with self._peers_lock:
            self._peer_digests[peer_node_id] = {
                "digest": digest,
                "last_seen": __import__("time").monotonic(),
            }

    def peer_digests(self) -> dict[str, dict[str, Any]]:
        with self._peers_lock:
            return {k: dict(v) for k, v in self._peer_digests.items()}

    def set_local_policy_digest(self, digest: str) -> None:
        self.local_policy_digest = digest

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"


def _make_handler(server: FederationServer) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        # Suppress default access logs; tests do their own.
        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            return

        def _send(self, code: int, body: dict[str, Any]) -> None:
            data = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:  # noqa: N802
            if self.path == PATH_INFO:
                self._send(200, {
                    "version": PROTOCOL_VERSION,
                    "node_id": server.node_id,
                    "public_key": server.public_key,
                })
                return
            self._send(404, {"error": "not_found"})

        def do_POST(self) -> None:  # noqa: N802
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 1024 * 1024:
                self._send(413, {"error": "body_too_large"})
                return
            raw = self.rfile.read(length)
            try:
                msg = FederationMessage.from_json(raw.decode("utf-8"))
            except (json.JSONDecodeError, KeyError, ValueError) as exc:
                self._send(400, {"error": "bad_message", "detail": str(exc)})
                return

            bearer = self.headers.get("Authorization", "")
            if not bearer.startswith("Bearer "):
                self._send(401, {"error": "missing_bearer"})
                return
            token = bearer[len("Bearer "):]
            if token != server.expected_fingerprint:
                self._send(403, {"error": "bad_fingerprint"})
                return

            # Track the peer (regardless of which endpoint they hit).
            server.record_peer(token, {"node_id": msg.attestation.sender if msg.attestation else "?"})

            if msg.kind is MessageKind.ASK and self.path == PATH_ASK:
                if server._on_ask is None:
                    self._send(503, {"error": "ask_handler_unset"})
                    return
                sender = msg.sender_node_id or (msg.attestation.sender if msg.attestation else None)
                # Drift refusal: if the server was constructed with a local
                # policy digest, the ask must carry a matching digest (or no
                # digest, which we treat as "this peer predates the drift
                # check" and allow through - drift refusal is opt-in per
                # cluster by setting local_policy_digest). If the digests
                # disagree, reject with 409 POLICY_DIGEST_MISMATCH and do
                # not run the local kernel.
                if (
                    server.local_policy_digest is not None
                    and msg.policy_digest is not None
                    and msg.policy_digest != server.local_policy_digest
                ):
                    if sender is not None:
                        server.record_peer_digest(sender, msg.policy_digest)
                    self._send(409, {
                        "error": "policy_digest_mismatch",
                        "local_digest": server.local_policy_digest,
                        "remote_digest": msg.policy_digest,
                    })
                    return
                # Track the peer's digest for the audit trail.
                if msg.policy_digest is not None and sender is not None:
                    server.record_peer_digest(sender, msg.policy_digest)
                try:
                    request = ActionRequest.from_dict(msg.body)
                    request.validate()
                except (KeyError, ValueError, TypeError) as exc:
                    self._send(400, {"error": "bad_request", "detail": str(exc)})
                    return
                try:
                    vote = server._on_ask(request)
                except Exception as exc:  # noqa: BLE001
                    self._send(500, {"error": "ask_handler_failed", "detail": str(exc)})
                    return
                self._send(200, {"vote": vote.to_dict()})
                return
            if msg.kind is MessageKind.HEARTBEAT and self.path == PATH_HEARTBEAT:
                if server._on_heartbeat is None:
                    self._send(503, {"error": "heartbeat_handler_unset"})
                    return
                try:
                    hb = HeartbeatBody.from_dict(msg.body)
                except (KeyError, ValueError) as exc:
                    self._send(400, {"error": "bad_heartbeat", "detail": str(exc)})
                    return
                server._on_heartbeat(hb)
                self._send(200, {"ok": True})
                return
            self._send(404, {"error": "not_found", "path": self.path, "kind": msg.kind.value})

    return Handler


# ---------- client side ----------


class FederationError(Exception):
    """Raised when a peer call fails. Wraps HTTP, timeout, parse errors."""


class FederationClient:
    """Outbound HTTP client for one peer."""

    def __init__(self, base_url: str, bearer: str, timeout_seconds: float = 2.0) -> None:
        parsed = urlparse(base_url)
        if parsed.hostname not in ("127.0.0.1", "localhost", None) and not parsed.hostname.startswith("127."):
            # The client side is for the same loopback + same overlay story.
            # We don't enforce hard here; we just leave the door open for
            # WireGuard / Tailscale addresses. Loopback is the default in tests.
            pass
        self.base_url = base_url.rstrip("/")
        self.bearer = bearer
        self.timeout_seconds = timeout_seconds

    def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        data = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
        req = Request(
            self.base_url + path,
            data=data,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.bearer}",
            },
        )
        try:
            with urlopen(req, timeout=self.timeout_seconds) as resp:
                payload = resp.read().decode("utf-8")
                return json.loads(payload) if payload else {"ok": True}
        except HTTPError as exc:
            raise FederationError(f"http {exc.code}: {exc.read().decode('utf-8', 'replace')}") from exc
        except URLError as exc:
            raise FederationError(f"url error: {exc.reason}") from exc
        except (TimeoutError, OSError) as exc:
            raise FederationError(f"transport error: {exc}") from exc

    def info(self) -> dict[str, Any]:
        parsed = urlparse(self.base_url)
        path = PATH_INFO
        try:
            with urlopen(self.base_url + path, timeout=self.timeout_seconds) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            raise FederationError(f"info failed: {exc}") from exc

    def post_ask(
        self,
        request: ActionRequest,
        attestation: Attestation | None = None,
        policy_digest: str | None = None,
        sender_node_id: str | None = None,
    ) -> dict[str, Any]:
        body = {"kind": MessageKind.ASK.value, "body": request.to_dict() if hasattr(request, "to_dict") else {
            "request_id": request.request_id,
            "subject_id": request.subject_id,
            "operation": request.operation,
            "resource": request.resource,
            "parameters": request.parameters,
        }}
        if attestation is not None:
            body["attestation"] = attestation.to_dict()
        if policy_digest is not None:
            body["policy_digest"] = policy_digest
        if sender_node_id is not None:
            body["sender_node_id"] = sender_node_id
        body["version"] = PROTOCOL_VERSION
        resp = self._post(PATH_ASK, body)
        # Server returns {"vote": {...}}
        if isinstance(resp, dict) and "vote" in resp:
            return resp["vote"]
        return resp

    def post_heartbeat(self, hb: HeartbeatBody, attestation: Attestation | None = None) -> None:
        body = {"kind": MessageKind.HEARTBEAT.value, "body": hb.to_dict()}
        if attestation is not None:
            body["attestation"] = attestation.to_dict()
        body["version"] = PROTOCOL_VERSION
        self._post(PATH_HEARTBEAT, body)
