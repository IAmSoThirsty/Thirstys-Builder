from __future__ import annotations

from pathlib import Path


PROJECT_VERSION = "0.3.1"
PACKAGE_NAME = f"constitutional-builder-{PROJECT_VERSION}.zip"
LOCAL_IMAGE_TAG = "constitutional-builder:local-verify"
RELEASE_IMAGE_TAG = f"constitutional-builder:{PROJECT_VERSION}"

LOCAL_METADATA_PARTS = {
    ".git",
    ".hermes",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tool-cache",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    "states",
    "target",
}

LOCAL_METADATA_PREFIXES = {
    ".github/instructions",
    "deploy/runtime",
}

RELEASE_GENERATED_PREFIXES = {
    "release/package-manifest.json",
    "release/package-signature.json",
    "release/signing-public-key.pem",
}


def repo_relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def is_local_metadata(relative: str) -> bool:
    parts = set(Path(relative).parts)
    if parts & LOCAL_METADATA_PARTS:
        return True
    return any(
        relative == prefix or relative.startswith(f"{prefix}/")
        for prefix in LOCAL_METADATA_PREFIXES
    )


def is_release_package(relative: str) -> bool:
    return relative.startswith("release/") and relative.endswith(".zip")


def is_generated_release_metadata(relative: str) -> bool:
    return relative in RELEASE_GENERATED_PREFIXES
