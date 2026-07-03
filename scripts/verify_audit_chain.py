from __future__ import annotations

import argparse
import json
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))

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
    ReplayVerifier,
    Subject,
)


def _build_kernel(audit_log=None) -> ConstitutionalKernel:
    return ConstitutionalKernel(
        identities=IdentityRegistry([Subject("operator", "Operator")]),
        policies=PolicyEngine(
            [PolicyRule("allow", PolicyEffect.ALLOW, "echo", "demo", "operator", "ok")]
        ),
        capabilities=CapabilityRegistry(
            [CapabilityGrant("grant", "operator", "echo", "demo")]
        ),
        audit_log=audit_log or InMemoryAuditLog(),
        handlers={"echo": lambda resource, parameters: {"ok": True, "resource": resource}},
    )


def _emit(kernel: ConstitutionalKernel, count: int) -> None:
    for i in range(count):
        kernel.handle(
            ActionRequest(
                request_id=f"chain-{i}",
                subject_id="operator",
                operation="echo",
                resource="demo",
                parameters={"i": i},
            )
        )


def check_inmemory_chain() -> str | None:
    kernel = _build_kernel()
    _emit(kernel, 10)
    report = ReplayVerifier().verify(kernel.audit_log.events)
    if not report.valid:
        return f"in-memory chain invalid: {report.reason}"
    if report.event_count != 10:
        return f"in-memory chain event count {report.event_count} != 10"
    return None


def check_file_chain_roundtrip() -> str | None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "audit.jsonl"
        log = FileAuditLog(path)
        kernel = _build_kernel(audit_log=log)
        _emit(kernel, 5)
        report = ReplayVerifier().verify(kernel.audit_log.events)
        if not report.valid:
            return f"file chain invalid during write: {report.reason}"
        reloaded = FileAuditLog(path)
        report = ReplayVerifier().verify(reloaded.events)
        if not report.valid:
            return f"file chain invalid after roundtrip: {report.reason}"
        if len(reloaded.events) != 5:
            return f"file chain event count {len(reloaded.events)} != 5"
    return None


def check_tamper_detected_inmemory() -> str | None:
    kernel = _build_kernel()
    _emit(kernel, 3)
    original = kernel.audit_log.events[1]
    tampered = replace(original, reason="tampered")
    kernel.audit_log._events[1] = tampered  # noqa: SLF001 - intentional corruption fixture.
    report = ReplayVerifier().verify(kernel.audit_log.events)
    if report.valid:
        return "in-memory chain accepted tampered event"
    return None


def check_tamper_detected_file() -> str | None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "audit.jsonl"
        log = FileAuditLog(path)
        kernel = _build_kernel(audit_log=log)
        _emit(kernel, 4)
        # Reopen the file, mutate the second line in place (a realistic
        # attacker scenario: rewrites history while the file is on disk).
        lines = path.read_text(encoding="utf-8").splitlines()
        parsed = [json.loads(line) for line in lines if line.strip()]
        parsed[1]["reason"] = "tampered-on-disk"
        # Rewrite only the file content; do NOT regenerate the chain hash.
        new_text = "\n".join(json.dumps(item) for item in parsed) + "\n"
        path.write_text(new_text, encoding="utf-8")
        reloaded = FileAuditLog(path)
        report = ReplayVerifier().verify(reloaded.events)
        if report.valid:
            return "file chain accepted on-disk tamper"
    return None


def check_federation_hash_deterministic() -> str | None:
    node_a = BuilderNode("node-a", _build_kernel())
    _emit(node_a.kernel, 3)
    node_b = BuilderNode("node-b", _build_kernel())
    _emit(node_b.kernel, 3)
    report_1 = FederationVerifier().verify((node_a, node_b))
    report_2 = FederationVerifier().verify((node_a, node_b))
    if not report_1.valid or not report_2.valid:
        return "federation verifier reports invalid on stable inputs"
    if report_1.federation_hash != report_2.federation_hash:
        return (
            f"federation hash is non-deterministic: {report_1.federation_hash} vs {report_2.federation_hash}"
        )
    return None


def check_federation_hash_changes_on_tamper() -> str | None:
    node_good = BuilderNode("node-good", _build_kernel())
    _emit(node_good.kernel, 3)
    node_bad_kernel = _build_kernel()
    _emit(node_bad_kernel, 3)
    node_bad_kernel.audit_log._events[2] = replace(  # noqa: SLF001
        node_bad_kernel.audit_log.events[2], reason="tampered"
    )
    node_bad = BuilderNode("node-bad", node_bad_kernel)
    good_report = FederationVerifier().verify((node_good,))
    bad_report = FederationVerifier().verify((node_bad,))
    if not good_report.valid:
        return f"good federation report invalid: {good_report.reason}"
    if bad_report.valid:
        return "bad federation report unexpectedly valid"
    if good_report.federation_hash == bad_report.federation_hash:
        return "federation hash did not change on tamper"
    return None


CHECKS = [
    ("in-memory chain integrity", check_inmemory_chain),
    ("file audit chain roundtrip", check_file_chain_roundtrip),
    ("in-memory tamper detection", check_tamper_detected_inmemory),
    ("on-disk tamper detection", check_tamper_detected_file),
    ("federation hash determinism", check_federation_hash_deterministic),
    ("federation hash changes on tamper", check_federation_hash_changes_on_tamper),
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON summary")
    args = parser.parse_args()

    failures: list[dict[str, str]] = []
    for name, check in CHECKS:
        result = check()
        if result is None:
            print(f"PASS: audit chain {name}")
        else:
            print(f"FAIL: audit chain {name}: {result}")
            failures.append({"check": name, "reason": result})

    if args.json:
        print(json.dumps({"passed": len(CHECKS) - len(failures), "failed": failures}, indent=2))

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
