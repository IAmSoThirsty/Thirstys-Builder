from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen


class BuilderClientError(RuntimeError):
    pass


@dataclass(frozen=True)
class BuilderClient:
    base_url: str
    timeout: float = 5.0

    def health(self) -> dict[str, Any]:
        return self._request("GET", "/health")

    def replay(self) -> dict[str, Any]:
        return self._request("GET", "/v1/replay")

    def audit(self) -> dict[str, Any]:
        return self._request("GET", "/v1/audit")

    def query(self, query: str) -> dict[str, Any]:
        return self._request("POST", "/v1/query", {"query": query})

    def grpc_compat(self, method: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._request("POST", "/v1/grpc", {"method": method, "payload": payload or {}})

    def execute(
        self,
        *,
        request_id: str,
        subject_id: str,
        operation: str,
        resource: str,
        parameters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/v1/execute",
            {
                "request_id": request_id,
                "subject_id": subject_id,
                "operation": operation,
                "resource": resource,
                "parameters": parameters or {},
            },
        )

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(
            self.base_url.rstrip("/") + path,
            data=data,
            method=method,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            body = exc.read().decode("utf-8")
            try:
                payload = json.loads(body)
            except json.JSONDecodeError:
                payload = {"error": body}
            raise BuilderClientError(f"{exc.code}: {payload}") from exc
