from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

try:
    from .release_config import (
        PACKAGE_NAME,
        is_generated_release_metadata,
        is_local_metadata,
        is_release_package,
        repo_relative,
    )
except ImportError:  # pragma: no cover - direct script execution
    from release_config import (
        PACKAGE_NAME,
        is_generated_release_metadata,
        is_local_metadata,
        is_release_package,
        repo_relative,
    )


ROOT = Path(__file__).resolve().parents[1]
RELEASE_DIR = ROOT / "release"
MANIFEST_NAME = "package-manifest.json"
FIXED_ZIP_DATE = (1980, 1, 1, 0, 0, 0)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build or check deterministic release package.")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    files = iter_package_files()
    manifest = build_manifest(files)
    package_bytes = build_zip_bytes(files)
    package_sha256 = hashlib.sha256(package_bytes).hexdigest()
    manifest["package"] = {
        "path": f"release/{PACKAGE_NAME}",
        "sha256": package_sha256,
        "size_bytes": len(package_bytes),
    }

    if args.check:
        failures: list[str] = []
        package_path = RELEASE_DIR / PACKAGE_NAME
        manifest_path = RELEASE_DIR / MANIFEST_NAME
        if not package_path.exists():
            failures.append(f"missing release package: release/{PACKAGE_NAME}")
        elif hashlib.sha256(package_path.read_bytes()).hexdigest() != package_sha256:
            failures.append(f"release/{PACKAGE_NAME} is stale")
        if not manifest_path.exists():
            failures.append(f"missing package manifest: release/{MANIFEST_NAME}")
        elif json.loads(manifest_path.read_text(encoding="utf-8")) != manifest:
            failures.append(f"release/{MANIFEST_NAME} is stale")
        if failures:
            for failure in failures:
                print(f"FAIL: {failure}")
            return 1
        print("PASS: release package is current")
        return 0

    RELEASE_DIR.mkdir(parents=True, exist_ok=True)
    (RELEASE_DIR / PACKAGE_NAME).write_bytes(package_bytes)
    (RELEASE_DIR / MANIFEST_NAME).write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print("PASS: release package built")
    return 0


def iter_package_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        relative = repo_relative(path, ROOT)
        if is_local_metadata(relative):
            continue
        if is_release_package(relative):
            continue
        if is_generated_release_metadata(relative):
            continue
        files.append(path)
    return sorted(files, key=lambda item: repo_relative(item, ROOT))


def build_manifest(files: list[Path]) -> dict[str, object]:
    entries = []
    for path in files:
        entries.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
        )
    return {
        "schema": "constitutional-builder-package-manifest-v1",
        "package_name": PACKAGE_NAME,
        "file_count": len(entries),
        "files": entries,
    }


def build_zip_bytes(files: list[Path]) -> bytes:
    import io

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            relative = repo_relative(path, ROOT)
            info = zipfile.ZipInfo(relative, FIXED_ZIP_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())
    return buffer.getvalue()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
