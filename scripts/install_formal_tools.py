from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "tools" / "formal-tools.lock.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Install pinned formal verification tools.")
    parser.add_argument("--write-hashes", action="store_true")
    args = parser.parse_args()

    data = json.loads(LOCK.read_text(encoding="utf-8"))
    changed = False
    for tool in data["tools"]:
        target = ROOT / tool["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            print(f"DOWNLOAD: {tool['name']} {tool['url']}")
            with urllib.request.urlopen(tool["url"], timeout=120) as response:
                target.write_bytes(response.read())
        digest = sha256_file(target)
        expected = tool.get("sha256")
        if expected and expected != digest:
            print(f"FAIL: {tool['name']} sha256 mismatch: expected {expected}, got {digest}")
            return 1
        if expected is None and args.write_hashes:
            tool["sha256"] = digest
            changed = True
        print(f"PASS: {tool['name']} installed sha256={digest}")

    if changed:
        LOCK.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print("PASS: formal tool lockfile hashes written")
    return 0


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
