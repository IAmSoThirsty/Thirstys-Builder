from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RELEASE_DIR = ROOT / "release"
EXCLUDED_DIRS = {
    ".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".tool-cache", "states", "target", "node_modules", "dist", "build",
}
EXCLUDED_PREFIXES = {"deploy/runtime"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate deterministic release evidence.")
    parser.add_argument("--check", action="store_true", help="fail if generated evidence differs")
    args = parser.parse_args()

    files = list(iter_source_files())
    sbom = build_sbom(files)
    provenance = build_provenance(files, sbom)
    signature = sign_provenance(provenance)

    expected = {
        "sbom.json": sbom,
        "provenance.json": provenance,
        "provenance.signature.json": signature,
    }

    if args.check:
        failures = []
        for name, payload in expected.items():
            path = RELEASE_DIR / name
            if not path.exists():
                failures.append(f"missing release evidence: release/{name}")
                continue
            current = json.loads(path.read_text(encoding="utf-8"))
            if current != payload:
                failures.append(f"release/{name} is stale")
        if failures:
            for failure in failures:
                print(f"FAIL: {failure}")
            return 1
        print("PASS: release evidence is current")
        return 0

    RELEASE_DIR.mkdir(parents=True, exist_ok=True)
    for name, payload in expected.items():
        (RELEASE_DIR / name).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print("PASS: release evidence generated")
    return 0


def iter_source_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(ROOT).as_posix()
        parts = set(Path(relative).parts)
        if parts & EXCLUDED_DIRS:
            continue
        if any(relative == excluded or relative.startswith(f"{excluded}/") for excluded in EXCLUDED_PREFIXES):
            continue
        if relative.startswith("release/"):
            continue
        files.append(path)
    return sorted(files, key=lambda item: item.relative_to(ROOT).as_posix())


def build_sbom(files: list[Path]) -> dict[str, object]:
    generated_utc = stable_timestamp(files)
    components = []
    for path in files:
        relative = path.relative_to(ROOT).as_posix()
        components.append(
            {
                "path": relative,
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "type": classify(relative),
            }
        )
    return {
        "schema": "constitutional-builder-sbom-v1",
        "generated_utc": generated_utc,
        "component_count": len(components),
        "components": components,
    }


def build_provenance(files: list[Path], sbom: dict[str, object]) -> dict[str, object]:
    tree_hash = hashlib.sha256()
    for path in files:
        relative = path.relative_to(ROOT).as_posix()
        tree_hash.update(relative.encode("utf-8"))
        tree_hash.update(b"\0")
        tree_hash.update(sha256_file(path).encode("ascii"))
        tree_hash.update(b"\n")
    return {
        "schema": "constitutional-builder-provenance-v1",
        "generated_utc": stable_timestamp(files),
        "builder": "local-codex",
        "source_root": str(ROOT),
        "tree_sha256": tree_hash.hexdigest(),
        "sbom_component_count": sbom["component_count"],
        "verification_command": "python scripts/verify_all.py",
    }


def sign_provenance(provenance: dict[str, object]) -> dict[str, object]:
    payload = json.dumps(provenance, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        "schema": "constitutional-builder-local-signature-v1",
        "algorithm": "sha256",
        "note": "Local integrity signature; replace with key-backed signing for external release.",
        "provenance_sha256": hashlib.sha256(payload).hexdigest(),
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def classify(relative: str) -> str:
    first = relative.split("/", 1)[0]
    if first in {"source", "tests", "scripts", "benchmarks", "sdk"}:
        return "software"
    if first in {"spec", "docs", "formal", "security", "commander"}:
        return "documentation"
    if first in {"deploy", "ci"}:
        return "deployment"
    if first == "examples":
        return "fixture"
    return "metadata"


def stable_timestamp(files: list[Path]) -> str:
    """Return a stable ISO 8601 UTC timestamp.

    For reproducible builds, respect `SOURCE_DATE_EPOCH` if set.
    Otherwise use the newest source file mtime so `--check` is stable
    while still reporting a real source-derived timestamp.
    """
    env_value = os.environ.get("SOURCE_DATE_EPOCH")
    if env_value:
        return datetime.fromtimestamp(int(env_value), tz=timezone.utc).isoformat()
    newest = max((path.stat().st_mtime for path in files), default=0)
    return datetime.fromtimestamp(int(newest), tz=timezone.utc).isoformat()


if __name__ == "__main__":
    raise SystemExit(main())
