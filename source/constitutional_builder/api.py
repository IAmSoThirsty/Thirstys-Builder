from __future__ import annotations

import argparse
import json
from dataclasses import asdict, is_dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
from pathlib import Path
from typing import Any

from .config import build_kernel_from_config, load_config
from .kernel import ConstitutionalKernel
from .models import ActionRequest
from .replay import ReplayVerifier


class KernelApiHandler(BaseHTTPRequestHandler):
    kernel: ConstitutionalKernel

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._json(
                HTTPStatus.OK,
                {
                    "status": "ok",
                    "audit_valid": self.kernel.audit_log.verify(),
                    "audit_event_count": len(self.kernel.audit_log.events),
                },
            )
            return
        if parsed.path == "/v1/replay":
            report = ReplayVerifier().verify(self.kernel.audit_log.events)
            self._json(HTTPStatus.OK if report.valid else HTTPStatus.CONFLICT, asdict(report))
            return
        if parsed.path == "/v1/audit":
            self._json(
                HTTPStatus.OK,
                {
                    "events": [_to_jsonable(event) for event in self.kernel.audit_log.events],
                    "event_count": len(self.kernel.audit_log.events),
                },
            )
            return
        if parsed.path == "/v1/audit/stream":
            self._event_stream(
                [
                    {"event": "audit", "data": _to_jsonable(event)}
                    for event in self.kernel.audit_log.events
                ]
            )
            return
        self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802 - stdlib handler API
        parsed = urlparse(self.path)
        if parsed.path == "/v1/query":
            self._handle_query()
            return
        if parsed.path == "/v1/grpc":
            self._handle_grpc_compat()
            return
        if parsed.path != "/v1/execute":
            self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return

        try:
            body = self._read_json()
            request = ActionRequest(
                request_id=body["request_id"],
                subject_id=body["subject_id"],
                operation=body["operation"],
                resource=body["resource"],
                parameters=body.get("parameters", {}),
            )
        except (KeyError, ValueError, json.JSONDecodeError) as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        decision = self.kernel.handle(request)
        status = HTTPStatus.OK if decision.allowed else HTTPStatus.FORBIDDEN
        self._json(status, _to_jsonable(decision))

    def _handle_grpc_compat(self) -> None:
        try:
            body = self._read_json()
            method = str(body["method"])
            payload = body.get("payload", {})
            if not isinstance(payload, dict):
                raise ValueError("payload must be a JSON object")
        except (KeyError, ValueError, json.JSONDecodeError) as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if method == "constitutional_builder.v1.BuilderService/Health":
            self._json(
                HTTPStatus.OK,
                {
                    "status": "ok",
                    "audit_valid": self.kernel.audit_log.verify(),
                    "audit_event_count": len(self.kernel.audit_log.events),
                },
            )
            return
        if method == "constitutional_builder.v1.BuilderService/Execute":
            try:
                request = ActionRequest(
                    request_id=str(payload["request_id"]),
                    subject_id=str(payload["subject_id"]),
                    operation=str(payload["operation"]),
                    resource=str(payload["resource"]),
                    parameters=dict(payload.get("parameters", {})),
                )
            except KeyError as exc:
                self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return
            decision = self.kernel.handle(request)
            self._json(HTTPStatus.OK if decision.allowed else HTTPStatus.FORBIDDEN, _to_jsonable(decision))
            return
        if method == "constitutional_builder.v1.BuilderService/Replay":
            self._json(HTTPStatus.OK, asdict(ReplayVerifier().verify(self.kernel.audit_log.events)))
            return
        if method == "constitutional_builder.v1.BuilderService/Audit":
            self._json(
                HTTPStatus.OK,
                {
                    "events": [_to_jsonable(event) for event in self.kernel.audit_log.events],
                    "event_count": len(self.kernel.audit_log.events),
                },
            )
            return
        self._json(HTTPStatus.BAD_REQUEST, {"error": "unsupported grpc method"})

    def _handle_query(self) -> None:
        try:
            body = self._read_json()
            query = str(body["query"]).strip()
        except (KeyError, ValueError, json.JSONDecodeError) as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if query == "{ health { status auditValid auditEventCount } }":
            self._json(
                HTTPStatus.OK,
                {
                    "data": {
                        "health": {
                            "status": "ok",
                            "auditValid": self.kernel.audit_log.verify(),
                            "auditEventCount": len(self.kernel.audit_log.events),
                        }
                    }
                },
            )
            return
        if query == "{ replay { valid eventCount reason } }":
            report = ReplayVerifier().verify(self.kernel.audit_log.events)
            self._json(
                HTTPStatus.OK,
                {
                    "data": {
                        "replay": {
                            "valid": report.valid,
                            "eventCount": report.event_count,
                            "reason": report.reason,
                        }
                    }
                },
            )
            return
        self._json(HTTPStatus.BAD_REQUEST, {"error": "unsupported query"})

    def log_message(self, format: str, *args: object) -> None:
        return

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8")
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError("request body must be a JSON object")
        return data

    def _json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _event_stream(self, events: list[dict[str, Any]]) -> None:
        chunks = []
        for event in events:
            chunks.append(f"event: {event['event']}\n")
            chunks.append(f"data: {json.dumps(event['data'], sort_keys=True, default=str)}\n\n")
        encoded = "".join(chunks).encode("utf-8")
        self.send_response(HTTPStatus.OK.value)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def make_server(kernel: ConstitutionalKernel, host: str, port: int) -> ThreadingHTTPServer:
    class Handler(KernelApiHandler):
        pass

    Handler.kernel = kernel
    return ThreadingHTTPServer((host, port), Handler)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Constitutional Builder HTTP API.")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8080, type=int)
    args = parser.parse_args()

    kernel = build_kernel_from_config(load_config(args.config))
    server = make_server(kernel, args.host, args.port)
    print(f"constitutional-builder-api listening on http://{args.host}:{args.port}")
    server.serve_forever()
    return 0


def _to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return {key: _to_jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {key: _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_to_jsonable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
