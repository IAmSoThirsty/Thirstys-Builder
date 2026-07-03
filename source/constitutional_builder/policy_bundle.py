from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .policy import PolicyEffect, PolicyRule


SUPPORTED_POLICY_BUNDLE_VERSION = "1.0"


@dataclass(frozen=True)
class PolicyBundle:
    bundle_id: str
    version: str
    rules: tuple[PolicyRule, ...]

    def validate(self) -> None:
        if self.version != SUPPORTED_POLICY_BUNDLE_VERSION:
            raise ValueError(f"unsupported policy bundle version: {self.version}")
        if not self.bundle_id:
            raise ValueError("bundle_id is required")
        policy_ids: set[str] = set()
        for rule in self.rules:
            if not rule.policy_id:
                raise ValueError("policy_id is required")
            if rule.policy_id in policy_ids:
                raise ValueError(f"duplicate policy_id: {rule.policy_id}")
            policy_ids.add(rule.policy_id)
            if not rule.operation:
                raise ValueError(f"{rule.policy_id}: operation is required")


def load_policy_bundle(path: str | Path) -> PolicyBundle:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    bundle = PolicyBundle(
        bundle_id=data["bundle_id"],
        version=data["version"],
        rules=tuple(
            PolicyRule(
                policy_id=item["policy_id"],
                effect=PolicyEffect(item["effect"]),
                operation=item["operation"],
                resource=item.get("resource", "*"),
                subject_id=item.get("subject_id", "*"),
                reason=item.get("reason", ""),
            )
            for item in data.get("rules", [])
        ),
    )
    bundle.validate()
    return bundle


def migrate_legacy_policy_list(
    *,
    bundle_id: str,
    policies: list[dict[str, str]],
) -> PolicyBundle:
    bundle = PolicyBundle(
        bundle_id=bundle_id,
        version=SUPPORTED_POLICY_BUNDLE_VERSION,
        rules=tuple(
            PolicyRule(
                policy_id=item["policy_id"],
                effect=PolicyEffect(item["effect"]),
                operation=item["operation"],
                resource=item.get("resource", "*"),
                subject_id=item.get("subject_id", "*"),
                reason=item.get("reason", ""),
            )
            for item in policies
        ),
    )
    bundle.validate()
    return bundle
