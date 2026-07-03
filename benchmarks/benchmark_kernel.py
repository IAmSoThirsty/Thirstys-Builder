from __future__ import annotations

import argparse
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "source"))

from constitutional_builder import (  # noqa: E402
    ActionRequest,
    CapabilityGrant,
    CapabilityRegistry,
    ConstitutionalKernel,
    IdentityRegistry,
    InMemoryAuditLog,
    PolicyEffect,
    PolicyEngine,
    PolicyRule,
    ReplayVerifier,
    Subject,
)


def build_kernel() -> ConstitutionalKernel:
    return ConstitutionalKernel(
        identities=IdentityRegistry([Subject("bench", "Benchmark Operator")]),
        policies=PolicyEngine([PolicyRule("bench-allow", PolicyEffect.ALLOW, "echo", "*", "bench")]),
        capabilities=CapabilityRegistry([CapabilityGrant("bench-grant", "bench", "echo", "*")]),
        audit_log=InMemoryAuditLog(),
        handlers={"echo": lambda resource, parameters: {"resource": resource, "parameters": parameters}},
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=1000)
    args = parser.parse_args()

    kernel = build_kernel()
    durations_ms: list[float] = []
    for index in range(args.iterations):
        request = ActionRequest(
            request_id=f"bench-{index}",
            subject_id="bench",
            operation="echo",
            resource="resource",
            parameters={"index": index},
        )
        start = time.perf_counter()
        decision = kernel.handle(request)
        durations_ms.append((time.perf_counter() - start) * 1000)
        if not decision.allowed:
            print(f"FAIL: benchmark request denied at iteration {index}: {decision.reason}")
            return 1

    replay = ReplayVerifier().verify(kernel.audit_log.events)
    if not replay.valid:
        print(f"FAIL: replay invalid: {replay.reason}")
        return 1

    p95 = statistics.quantiles(durations_ms, n=20)[18] if len(durations_ms) >= 20 else max(durations_ms)
    print(
        "PASS: "
        f"iterations={args.iterations} "
        f"min_ms={min(durations_ms):.4f} "
        f"mean_ms={statistics.mean(durations_ms):.4f} "
        f"p95_ms={p95:.4f} "
        f"max_ms={max(durations_ms):.4f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
