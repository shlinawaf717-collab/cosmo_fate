#!/usr/bin/env python3
"""Verify every registered WP4 likelihood input by path, bytes, and SHA256."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    failures = []
    checked = 0
    checked_bytes = 0
    for group_name, group in manifest["groups"].items():
        for record in group["files"]:
            path = args.root / record["path"]
            if not path.is_file():
                failures.append({"group": group_name, "path": record["path"], "error": "missing"})
                continue
            size = path.stat().st_size
            digest = sha256_file(path)
            checked += 1
            checked_bytes += size
            if size != record["bytes"] or digest != record["sha256"]:
                failures.append({
                    "group": group_name, "path": record["path"],
                    "expected_bytes": record["bytes"], "actual_bytes": size,
                    "expected_sha256": record["sha256"], "actual_sha256": digest,
                })
    payload = {
        "schema_version": "wp4-f1-wsl2-input-verification-v1",
        "status": "PASS" if not failures else "FAIL",
        "checked_files": checked,
        "checked_bytes": checked_bytes,
        "registered_totals": manifest["totals"],
        "failures": failures,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "checked_files": checked, "failures": len(failures)}))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
