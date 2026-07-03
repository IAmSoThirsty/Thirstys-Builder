from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "release" / "constitutional-builder-0.1.0.zip"
SIGNATURE = ROOT / "release" / "package-signature.json"
PUBLIC_KEY = ROOT / "release" / "signing-public-key.pem"
TEST_SEED = hashlib.sha256(b"constitutional-builder-local-test-signing-key-v1").digest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Sign or verify the release package.")
    parser.add_argument("--check", action="store_true")
    parser.add_argument(
        "--production",
        action="store_true",
        help="require CONSTITUTIONAL_BUILDER_ED25519_PRIVATE_KEY_PEM instead of local test key",
    )
    args = parser.parse_args()

    if args.check:
        return check_signature()

    private_key = load_private_key(require_env=args.production)
    public_key = private_key.public_key()
    package_bytes = PACKAGE.read_bytes()
    signature_bytes = private_key.sign(package_bytes)
    payload = {
        "schema": "constitutional-builder-ed25519-package-signature-v1",
        "package": "release/constitutional-builder-0.1.0.zip",
        "package_sha256": hashlib.sha256(package_bytes).hexdigest(),
        "algorithm": "Ed25519",
        "signature_base64": base64.b64encode(signature_bytes).decode("ascii"),
        "key_scope": "production-env" if args.production else "local-test-key",
        "note": (
            "Local test key is deterministic and not a production secret."
            if not args.production
            else "Signature created from configured production key material."
        ),
    }
    SIGNATURE.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    PUBLIC_KEY.write_bytes(
        public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    print("PASS: release package signed")
    return 0


def check_signature() -> int:
    failures: list[str] = []
    if not SIGNATURE.exists():
        failures.append("missing release/package-signature.json")
    if not PUBLIC_KEY.exists():
        failures.append("missing release/signing-public-key.pem")
    if not PACKAGE.exists():
        failures.append("missing release/constitutional-builder-0.1.0.zip")
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    payload = json.loads(SIGNATURE.read_text(encoding="utf-8"))
    package_bytes = PACKAGE.read_bytes()
    package_sha256 = hashlib.sha256(package_bytes).hexdigest()
    if payload.get("package_sha256") != package_sha256:
        print("FAIL: package signature references stale package hash")
        return 1

    public_key = serialization.load_pem_public_key(PUBLIC_KEY.read_bytes())
    if not isinstance(public_key, Ed25519PublicKey):
        print("FAIL: signing public key is not Ed25519")
        return 1
    try:
        public_key.verify(base64.b64decode(payload["signature_base64"]), package_bytes)
    except (InvalidSignature, KeyError, ValueError) as exc:
        print(f"FAIL: package signature verification failed: {exc}")
        return 1

    print("PASS: release package signature verified")
    return 0


def load_private_key(*, require_env: bool) -> Ed25519PrivateKey:
    pem = os.environ.get("CONSTITUTIONAL_BUILDER_ED25519_PRIVATE_KEY_PEM")
    if pem:
        key = serialization.load_pem_private_key(pem.encode("utf-8"), password=None)
        if not isinstance(key, Ed25519PrivateKey):
            raise TypeError("CONSTITUTIONAL_BUILDER_ED25519_PRIVATE_KEY_PEM must be Ed25519")
        return key
    if require_env:
        raise RuntimeError("production signing requires CONSTITUTIONAL_BUILDER_ED25519_PRIVATE_KEY_PEM")
    return Ed25519PrivateKey.from_private_bytes(TEST_SEED)


if __name__ == "__main__":
    raise SystemExit(main())
