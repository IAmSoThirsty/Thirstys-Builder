from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .audit import FileAuditLog, InMemoryAuditLog
from .capability import CapabilityGrant, CapabilityRegistry
from .identity import IdentityRegistry, Subject
from .kernel import ConstitutionalKernel, Handler
from .policy import PolicyEffect, PolicyEngine, PolicyRule


@dataclass(frozen=True)
class KernelConfig:
    subjects: tuple[Subject, ...]
    policies: tuple[PolicyRule, ...]
    capabilities: tuple[CapabilityGrant, ...]
    audit_log_path: Path | None = None


def load_config(path: str | Path) -> KernelConfig:
    config_path = Path(path)
    data = json.loads(config_path.read_text(encoding="utf-8"))

    subjects = tuple(
        Subject(
            subject_id=item["subject_id"],
            display_name=item.get("display_name", item["subject_id"]),
            roles=tuple(item.get("roles", [])),
            active=bool(item.get("active", True)),
        )
        for item in data.get("subjects", [])
    )
    policies = tuple(
        PolicyRule(
            policy_id=item["policy_id"],
            effect=PolicyEffect(item["effect"]),
            operation=item["operation"],
            resource=item.get("resource", "*"),
            subject_id=item.get("subject_id", "*"),
            reason=item.get("reason", ""),
        )
        for item in data.get("policies", [])
    )
    capabilities = tuple(
        CapabilityGrant(
            grant_id=item["grant_id"],
            subject_id=item["subject_id"],
            operation=item["operation"],
            resource=item.get("resource", "*"),
        )
        for item in data.get("capabilities", [])
    )
    audit_log_path = data.get("audit_log_path")
    return KernelConfig(
        subjects=subjects,
        policies=policies,
        capabilities=capabilities,
        audit_log_path=(config_path.parent / audit_log_path).resolve() if audit_log_path else None,
    )


def build_kernel_from_config(
    config: KernelConfig,
    *,
    handlers: dict[str, Handler] | None = None,
) -> ConstitutionalKernel:
    audit_log = FileAuditLog(config.audit_log_path) if config.audit_log_path else InMemoryAuditLog()
    return ConstitutionalKernel(
        identities=IdentityRegistry(list(config.subjects)),
        policies=PolicyEngine(list(config.policies)),
        capabilities=CapabilityRegistry(list(config.capabilities)),
        audit_log=audit_log,
        handlers=handlers or default_handlers(),
    )


def default_handlers() -> dict[str, Handler]:
    return {
        "echo": lambda resource, parameters: {"resource": resource, "parameters": parameters},
        "record_evidence": _record_evidence,
    }


def _record_evidence(resource: str, parameters: dict[str, Any]) -> dict[str, Any]:
    evidence_id = parameters.get("evidence_id")
    if not evidence_id:
        raise ValueError("evidence_id is required")
    return {
        "resource": resource,
        "evidence_id": evidence_id,
        "recorded": True,
        "summary": parameters.get("summary", ""),
    }
