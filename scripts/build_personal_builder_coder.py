"""Build the personal-builder-coder Ollama model from this repo.

Reproduces the `personal-builder-coder:v0.4.0-prep` tag from a fresh
checkout using the in-repo Modelfile and the source-evidence
manifest. Does NOT call Ollama's registry - the upstream Qwen
2.5 Coder 7B base is assumed already present (it's a standard
Ollama model).

Usage:
    python scripts/build_personal_builder_coder.py              # build
    python scripts/build_personal_builder_coder.py --check      # verify only
    python scripts/build_personal_builder_coder.py --remove     # unbuild (delete the tag)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "models" / "personal-builder-coder"
MODELFILE = MODEL_DIR / "Modelfile"
MANIFEST = MODEL_DIR / "manifest.json"
SOURCE_EVIDENCE = MODEL_DIR / "source-evidence.json"
SIGNATURE = MODEL_DIR / "manifest.signature.json"
PUBLIC_KEY = ROOT / "release" / "signing-public-key.pem"

EXPECTED_TAG = "personal-builder-coder:v0.4.0-prep"
EXPECTED_BASE = "qwen2.5-coder:7b"


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def canonical_json(obj: dict) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def check_manifest() -> int:
    """Verify the manifest is current and signed correctly. Returns 0 on success, 1 on failure."""
    if not MANIFEST.exists():
        print(f"FAIL: {MANIFEST} missing")
        return 1
    if not SIGNATURE.exists():
        print(f"FAIL: {SIGNATURE} missing")
        return 1
    if not MODELFILE.exists():
        print(f"FAIL: {MODELFILE} missing")
        return 1
    if not SOURCE_EVIDENCE.exists():
        print(f"FAIL: {SOURCE_EVIDENCE} missing")
        return 1
    if not PUBLIC_KEY.exists():
        print(f"FAIL: {PUBLIC_KEY} missing (release signing key)")
        return 1

    manifest_obj = json.loads(MANIFEST.read_text(encoding="utf-8"))
    sig_obj = json.loads(SIGNATURE.read_text(encoding="utf-8"))
    se_obj = json.loads(SOURCE_EVIDENCE.read_text(encoding="utf-8"))

    # 1. Modelfile sha matches the manifest's recorded value
    actual_modelfile_sha = sha256_file(MODELFILE)
    if manifest_obj["files"]["Modelfile"]["sha256"] != actual_modelfile_sha:
        print(f"FAIL: Modelfile sha mismatch")
        print(f"  manifest: {manifest_obj['files']['Modelfile']['sha256']}")
        print(f"  actual:   {actual_modelfile_sha}")
        return 1
    print(f"PASS: Modelfile sha matches manifest ({actual_modelfile_sha[:16]}...)")

    # 2. source-evidence.json sha matches
    actual_se_sha = sha256_file(SOURCE_EVIDENCE)
    if manifest_obj["files"]["source-evidence.json"]["sha256"] != actual_se_sha:
        print(f"FAIL: source-evidence.json sha mismatch")
        return 1
    print(f"PASS: source-evidence.json sha matches manifest ({actual_se_sha[:16]}...)")

    # 3. Ed25519 signature verifies against the release public key
    try:
        from cryptography.hazmat.primitives.serialization import load_pem_public_key
        from cryptography.exceptions import InvalidSignature
        pub = load_pem_public_key(PUBLIC_KEY.read_bytes())
        sig = __import__("base64").b64decode(sig_obj["signature_base64"])
        pub.verify(sig, canonical_json(manifest_obj))
        print("PASS: manifest signature verifies against release public key")
    except (InvalidSignature, Exception) as e:
        print(f"FAIL: manifest signature invalid: {e}")
        return 1

    # 4. Every source paper exists and its hash matches
    bad = []
    for paper in se_obj["papers"]:
        if not paper["exists"]:
            bad.append(f"missing: {paper['filename']}")
            continue
        path = Path(paper["path"])
        if not path.exists():
            bad.append(f"missing on disk: {paper['filename']}")
            continue
        actual = sha256_file(path)
        if actual != paper["sha256"]:
            bad.append(f"sha mismatch: {paper['filename']} (recorded {paper['sha256'][:16]}, actual {actual[:16]})")
    if bad:
        print(f"FAIL: {len(bad)} source paper(s) failed integrity check:")
        for b in bad:
            print(f"  - {b}")
        return 1
    print(f"PASS: {se_obj['paper_count']} source papers present with matching SHA-256")

    return 0


def build() -> int:
    if not check_manifest() == 0:
        return 1

    # Verify the upstream base is present in Ollama
    r = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=30, shell=True)
    if EXPECTED_BASE not in r.stdout:
        print(f"FAIL: upstream base {EXPECTED_BASE!r} not in 'ollama list'")
        print("  Run: ollama pull qwen2.5-coder:7b")
        return 1
    print(f"PASS: upstream base {EXPECTED_BASE} present in ollama")

    # Check if the tag already exists
    r = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=30, shell=True)
    if EXPECTED_TAG in r.stdout:
        print(f"PASS: tag {EXPECTED_TAG} already exists, --remove first to rebuild")
        return 0

    # Create the model from the Modelfile
    print(f"RUN: ollama create {EXPECTED_TAG} -f {MODELFILE}")
    r = subprocess.run(
        ["ollama", "create", EXPECTED_TAG, "-f", str(MODELFILE)],
        capture_output=True, text=True, timeout=300, shell=True,
    )
    if r.returncode != 0:
        print(f"FAIL: ollama create exited {r.returncode}")
        print(r.stdout[-2000:])
        print(r.stderr[-2000:])
        return 1
    print(f"PASS: created {EXPECTED_TAG}")
    return 0


def remove() -> int:
    r = subprocess.run(["ollama", "rm", EXPECTED_TAG], capture_output=True, text=True, timeout=30, shell=True)
    if r.returncode == 0:
        print(f"PASS: removed {EXPECTED_TAG}")
        return 0
    else:
        print(f"FAIL: ollama rm exited {r.returncode}: {r.stderr}")
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the personal-builder-coder Ollama model from this repo.")
    parser.add_argument("--check", action="store_true", help="Verify manifest + signature only, do not build")
    parser.add_argument("--remove", action="store_true", help="Remove the tag from ollama")
    args = parser.parse_args()

    if args.check:
        return check_manifest()
    if args.remove:
        return remove()
    return build()


if __name__ == "__main__":
    raise SystemExit(main())
