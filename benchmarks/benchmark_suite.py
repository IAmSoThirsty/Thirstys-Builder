from __future__ import annotations

import argparse
import statistics
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "source"))

from constitutional_builder import (  # noqa: E402
    ActionRequest,
    BuilderNode,
    CapabilityGrant,
    CapabilityRegistry,
    ConstitutionalKernel,
    DecisionStatus,
    FederationVerifier,
    FileAuditLog,
    IdentityRegistry,
    InMemoryAuditLog,
    PolicyEffect,
    PolicyEngine,
    PolicyRule,
    QuorumCluster,
    ReplayVerifier,
    Subject,
    migrate_legacy_policy_list,
)


def _summarize(label: str, durations_ms: list[float], iterations: int) -> None:
    p95 = (
        statistics.quantiles(durations_ms, n=20)[18]
        if len(durations_ms) >= 20
        else max(durations_ms)
    )
    print(
        f"PASS: benchmark {label} "
        f"iterations={iterations} "
        f"min_ms={min(durations_ms):.4f} "
        f"mean_ms={statistics.mean(durations_ms):.4f} "
        f"p95_ms={p95:.4f} "
        f"max_ms={max(durations_ms):.4f}"
    )


def benchmark_audit(iterations: int) -> None:
    """InMemoryAuditLog append + verify_chain."""
    log = InMemoryAuditLog()
    durations: list[float] = []
    for index in range(iterations):
        start = time.perf_counter()
        log.append(
            request_id=f"a-{index}",
            subject_id="bench",
            operation="echo",
            resource="resource",
            status=DecisionStatus.ALLOWED.value,
            reason="bench",
            metadata={"index": index},
        )
        durations.append((time.perf_counter() - start) * 1000)
    if not log.verify():
        print("FAIL: audit chain invalid at end of benchmark")
        raise SystemExit(1)
    _summarize("audit", durations, iterations)


def benchmark_audit_file_persistence(iterations: int) -> None:
    """FileAuditLog write + read-back. Uses a temp file; cleans up."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "audit.jsonl"
        log = FileAuditLog(path)
        durations: list[float] = []
        for index in range(iterations):
            start = time.perf_counter()
            log.append(
                request_id=f"f-{index}",
                subject_id="bench",
                operation="echo",
                resource="resource",
                status=DecisionStatus.ALLOWED.value,
                reason="bench",
                metadata={"index": index},
            )
            durations.append((time.perf_counter() - start) * 1000)
        reloaded = FileAuditLog(path)
        if len(reloaded.events) != iterations:
            print(f"FAIL: file audit roundtrip count {len(reloaded.events)} != {iterations}")
            raise SystemExit(1)
    _summarize("audit-file", durations, iterations)


def benchmark_policy_evaluation(iterations: int) -> None:
    """PolicyEngine.evaluate over a 16-rule policy set, 50% allow / 50% deny."""
    rules = []
    for i in range(16):
        if i % 2 == 0:
            rules.append(PolicyRule(f"allow-{i}", PolicyEffect.ALLOW, f"op-{i}", "*", "bench"))
        else:
            rules.append(PolicyRule(f"deny-{i}", PolicyEffect.DENY, f"op-{i}", "*", "*", "bench-deny"))
    engine = PolicyEngine(rules)
    durations: list[float] = []
    for index in range(iterations):
        op = f"op-{index % 16}"
        request = ActionRequest(
            request_id=f"p-{index}",
            subject_id="bench",
            operation=op,
            resource="resource",
        )
        start = time.perf_counter()
        decision = engine.evaluate(request)
        durations.append((time.perf_counter() - start) * 1000)
        if (index % 2 == 0) != decision.allowed:
            print(f"FAIL: policy decision {decision.allowed} for op {op} at {index}")
            raise SystemExit(1)
    _summarize("policy", durations, iterations)


def benchmark_capability_check(iterations: int) -> None:
    """CapabilityRegistry.check over a 32-grant set, alternating matches."""
    grants = [CapabilityGrant(f"g-{i}", "bench", f"op-{i}", "*") for i in range(32)]
    registry = CapabilityRegistry(grants)
    durations: list[float] = []
    for index in range(iterations):
        op = f"op-{index % 32}"
        request = ActionRequest(
            request_id=f"c-{index}",
            subject_id="bench",
            operation=op,
            resource="resource",
        )
        start = time.perf_counter()
        decision = registry.check(request)
        durations.append((time.perf_counter() - start) * 1000)
        if not decision.allowed:
            print(f"FAIL: capability decision denied for {op} at {index}")
            raise SystemExit(1)
    _summarize("capability", durations, iterations)


def benchmark_cluster(iterations: int) -> None:
    """QuorumCluster.submit with 3 BuilderNodes, all configured to allow."""
    nodes = []
    for n in range(3):
        log = InMemoryAuditLog()
        kernel = ConstitutionalKernel(
            identities=IdentityRegistry([Subject("bench", "Bench")]),
            policies=PolicyEngine([PolicyRule("allow", PolicyEffect.ALLOW, "echo", "*", "bench")]),
            capabilities=CapabilityRegistry([CapabilityGrant("grant", "bench", "echo", "*")]),
            audit_log=log,
            handlers={"echo": lambda r, p: {"ok": True}},
        )
        nodes.append(BuilderNode(f"node-{n + 1}", kernel))
    cluster = QuorumCluster(nodes)  # default quorum = len(nodes)//2 + 1 = 2
    durations: list[float] = []
    for index in range(iterations):
        request = ActionRequest(
            request_id=f"cl-{index}",
            subject_id="bench",
            operation="echo",
            resource="resource",
        )
        start = time.perf_counter()
        decision = cluster.submit(request)
        durations.append((time.perf_counter() - start) * 1000)
        if not decision.allowed:
            print(f"FAIL: cluster denied at {index}: {decision.reason}")
            raise SystemExit(1)
    _summarize("cluster", durations, iterations)


def benchmark_federation(iterations: int) -> None:
    """FederationVerifier.verify on 5 node audit chains (10 events each)."""
    nodes = []
    for n in range(5):
        log = InMemoryAuditLog()
        for i in range(10):
            log.append(
                request_id=f"{n}-{i}",
                subject_id="bench",
                operation="echo",
                resource="resource",
                status=DecisionStatus.ALLOWED.value,
                reason="bench",
                metadata={"node": n, "index": i},
            )
        kernel = ConstitutionalKernel(
            identities=IdentityRegistry([Subject("bench", "Bench")]),
            policies=PolicyEngine([PolicyRule("allow", PolicyEffect.ALLOW, "echo", "*", "bench")]),
            capabilities=CapabilityRegistry([CapabilityGrant("grant", "bench", "echo", "*")]),
            audit_log=log,
        )
        nodes.append(BuilderNode(f"node-{n + 1}", kernel))
    verifier = FederationVerifier()
    durations: list[float] = []
    last_hash = ""
    for index in range(iterations):
        start = time.perf_counter()
        report = verifier.verify(tuple(nodes))
        durations.append((time.perf_counter() - start) * 1000)
        if not report.valid:
            print(f"FAIL: federation report invalid at {index}: {report.reason}")
            raise SystemExit(1)
        last_hash = report.federation_hash
    print(
        f"PASS: benchmark federation iterations={iterations} "
        f"federation_hash={last_hash[:16]}..."
    )


def benchmark_policy_bundle(iterations: int) -> None:
    """migrate_legacy_policy_list + PolicyBundle.validate over a 64-rule bundle."""
    raw_policies = [
        {
            "policy_id": f"p-{i}",
            "effect": "allow" if i % 2 == 0 else "deny",
            "operation": f"op-{i % 16}",
            "resource": "*",
            "subject_id": "bench",
            "reason": "bench",
        }
        for i in range(64)
    ]
    durations: list[float] = []
    for index in range(iterations):
        start = time.perf_counter()
        bundle = migrate_legacy_policy_list(bundle_id=f"bench-{index}", policies=raw_policies)
        bundle.validate()
        durations.append((time.perf_counter() - start) * 1000)
        if len(bundle.rules) != 64:
            print(f"FAIL: bundle rule count mismatch at {index}")
            raise SystemExit(1)
    _summarize("policy-bundle", durations, iterations)


BENCHMARKS = {
    "audit": benchmark_audit,
    "audit-file": benchmark_audit_file_persistence,
    "policy": benchmark_policy_evaluation,
    "capability": benchmark_capability_check,
    "cluster": benchmark_cluster,
    "federation": benchmark_federation,
    "policy-bundle": benchmark_policy_bundle,
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=1000)
    parser.add_argument(
        "--only",
        nargs="*",
        default=None,
        help="Run only these benchmark names. Default: all.",
    )
    args = parser.parse_args()

    selected = args.only or list(BENCHMARKS.keys())
    for name in selected:
        if name not in BENCHMARKS:
            print(f"FAIL: unknown benchmark {name!r}")
            return 1
        BENCHMARKS[name](args.iterations)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
