from __future__ import annotations

import argparse
from concurrent import futures
from pathlib import Path

import grpc

from .config import build_kernel_from_config, load_config
from .kernel import ConstitutionalKernel
from .models import ActionRequest
from .replay import ReplayVerifier
from .v1 import builder_pb2, builder_pb2_grpc


class BuilderService(builder_pb2_grpc.BuilderServiceServicer):
    def __init__(self, kernel: ConstitutionalKernel) -> None:
        self.kernel = kernel

    def Health(self, request, context):  # noqa: N802
        return builder_pb2.HealthResponse(
            status="ok",
            audit_valid=self.kernel.audit_log.verify(),
            audit_event_count=len(self.kernel.audit_log.events),
        )

    def Execute(self, request, context):  # noqa: N802
        decision = self.kernel.handle(
            ActionRequest(
                request_id=request.request_id,
                subject_id=request.subject_id,
                operation=request.operation,
                resource=request.resource,
                parameters=dict(request.parameters),
            )
        )
        return builder_pb2.DecisionResponse(
            request_id=decision.request_id,
            status=decision.status.value,
            reason=decision.reason,
            audit_event_id=decision.audit_event_id,
        )

    def Replay(self, request, context):  # noqa: N802
        report = ReplayVerifier().verify(self.kernel.audit_log.events)
        return builder_pb2.ReplayResponse(
            valid=report.valid,
            event_count=report.event_count,
            reason=report.reason,
        )

    def Audit(self, request, context):  # noqa: N802
        return builder_pb2.AuditResponse(
            events=[
                builder_pb2.AuditEvent(
                    event_id=event.event_id,
                    request_id=event.request_id,
                    subject_id=event.subject_id,
                    operation=event.operation,
                    resource=event.resource,
                    status=event.status,
                    reason=event.reason,
                    previous_hash=event.previous_hash,
                    event_hash=event.event_hash,
                )
                for event in self.kernel.audit_log.events
            ],
            event_count=len(self.kernel.audit_log.events),
        )


def make_grpc_server(kernel: ConstitutionalKernel, port: int = 0) -> grpc.Server:
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    builder_pb2_grpc.add_BuilderServiceServicer_to_server(BuilderService(kernel), server)
    server.add_insecure_port(f"127.0.0.1:{port}")
    return server


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the native gRPC Builder service.")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--port", type=int, default=50051)
    args = parser.parse_args()

    server = make_grpc_server(build_kernel_from_config(load_config(args.config)), args.port)
    server.start()
    print(f"constitutional-builder-grpc listening on 127.0.0.1:{args.port}")
    server.wait_for_termination()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
