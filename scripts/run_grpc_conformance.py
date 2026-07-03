from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))

import grpc  # noqa: E402

from constitutional_builder import (  # noqa: E402
    CapabilityGrant,
    CapabilityRegistry,
    ConstitutionalKernel,
    IdentityRegistry,
    InMemoryAuditLog,
    PolicyEffect,
    PolicyEngine,
    PolicyRule,
    Subject,
)
from constitutional_builder.grpc_server import make_grpc_server  # noqa: E402
from constitutional_builder.v1 import builder_pb2, builder_pb2_grpc  # noqa: E402


def main() -> int:
    kernel = ConstitutionalKernel(
        identities=IdentityRegistry([Subject("operator", "Operator")]),
        policies=PolicyEngine(
            [PolicyRule("grpc-allow", PolicyEffect.ALLOW, "echo", "demo", "operator")]
        ),
        capabilities=CapabilityRegistry([CapabilityGrant("grpc-grant", "operator", "echo", "demo")]),
        audit_log=InMemoryAuditLog(),
        handlers={"echo": lambda resource, parameters: {"resource": resource, "parameters": parameters}},
    )
    server = make_grpc_server(kernel, 0)
    port = server.add_insecure_port("127.0.0.1:0")
    server.start()
    try:
        with grpc.insecure_channel(f"127.0.0.1:{port}") as channel:
            stub = builder_pb2_grpc.BuilderServiceStub(channel)
            health = stub.Health(builder_pb2.HealthRequest(), timeout=5)
            if health.status != "ok" or not health.audit_valid:
                print(f"FAIL: bad health response: {health}")
                return 1
            decision = stub.Execute(
                builder_pb2.ExecuteRequest(
                    request_id="grpc-conf-1",
                    subject_id="operator",
                    operation="echo",
                    resource="demo",
                    parameters={"message": "native-grpc"},
                ),
                timeout=5,
            )
            if decision.status != "allowed":
                print(f"FAIL: expected allowed decision, got {decision.status}: {decision.reason}")
                return 1
            replay = stub.Replay(builder_pb2.ReplayRequest(), timeout=5)
            if not replay.valid or replay.event_count != 1:
                print(f"FAIL: replay failed: {replay}")
                return 1
            audit = stub.Audit(builder_pb2.AuditRequest(), timeout=5)
            if audit.event_count != 1 or audit.events[0].request_id != "grpc-conf-1":
                print(f"FAIL: audit response mismatch: {audit}")
                return 1
    finally:
        server.stop(grace=0)

    print("PASS: native gRPC conformance passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
