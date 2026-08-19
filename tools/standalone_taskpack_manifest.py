#!/usr/bin/env python3
"""Build or verify composite manifests for self-contained Windows task packs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path


COMMON_ADDED = (
    "README_STANDALONE_中文.md",
    "tools/standalone_taskpack_manifest.py",
    "windows/START_1_INSTALL_AND_PREFLIGHT.cmd",
    "windows/START_2_RUN.cmd",
    "windows/STATUS.cmd",
    "windows/PACKAGE_RESULTS.cmd",
    "wsl/90_standalone_preflight.sh",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def record(root: Path, relative: str) -> dict:
    path = root / relative
    return {"path": relative, "bytes": path.stat().st_size, "sha256": sha256(path)}


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
        temporary = Path(stream.name)
    os.replace(temporary, path)


def build(root: Path, kind: str, increment: str, wsl_root: str, output: Path) -> dict:
    added = list(COMMON_ADDED)
    if kind == "wp4_nested":
        added.append("work/f1/external_monitor/final_stop_audit.json")
    layers = []
    for layer_root, manifest_name in ((".", "PACKAGE_MANIFEST.json"), (increment, "INCREMENT_MANIFEST.json")):
        manifest = root / layer_root / manifest_name
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        layers.append({
            "root": layer_root,
            "manifest": manifest_name,
            "manifest_sha256": sha256(manifest),
            "registered_files": len(payload["files"]),
        })
    payload = {
        "schema_version": "standalone-windows-taskpack-v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "kind": kind,
        "identity": root.name,
        "wsl_install_root": wsl_root,
        "self_contained_likelihood_data": True,
        "requires_existing_wp4_taskpack_on_windows": False,
        "layers": layers,
        "added_files": [record(root, relative) for relative in added],
    }
    atomic_json(output, payload)
    return payload


def verify(root: Path, manifest: Path) -> dict:
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    failures = []
    checked = 0
    for layer in payload["layers"]:
        layer_root = root if layer["root"] == "." else root / layer["root"]
        layer_manifest = layer_root / layer["manifest"]
        if not layer_manifest.is_file() or sha256(layer_manifest) != layer["manifest_sha256"]:
            failures.append({"path": str(layer_manifest), "reason": "layer_manifest_hash"})
            continue
        registered = json.loads(layer_manifest.read_text(encoding="utf-8"))["files"]
        if len(registered) != layer["registered_files"]:
            failures.append({"path": str(layer_manifest), "reason": "layer_file_count"})
        for item in registered:
            path = layer_root / item["path"]
            checked += 1
            if not path.is_file():
                failures.append({"path": str(path), "reason": "missing"})
            elif path.stat().st_size != item["bytes"]:
                failures.append({"path": str(path), "reason": "bytes"})
            elif sha256(path) != item["sha256"]:
                failures.append({"path": str(path), "reason": "sha256"})
    for item in payload["added_files"]:
        path = root / item["path"]
        checked += 1
        if not path.is_file():
            failures.append({"path": str(path), "reason": "missing"})
        elif path.stat().st_size != item["bytes"]:
            failures.append({"path": str(path), "reason": "bytes"})
        elif sha256(path) != item["sha256"]:
            failures.append({"path": str(path), "reason": "sha256"})
    result = {
        "schema_version": "standalone-windows-taskpack-verification-v1",
        "status": "PASS" if not failures else "FAIL",
        "identity": payload["identity"],
        "checked_files": checked,
        "failures": failures,
    }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    make = subparsers.add_parser("build")
    make.add_argument("--root", type=Path, required=True)
    make.add_argument("--kind", choices=("wp4_nested", "wp5_bin4"), required=True)
    make.add_argument("--increment", required=True)
    make.add_argument("--wsl-root", required=True)
    make.add_argument("--output", type=Path)
    check = subparsers.add_parser("verify")
    check.add_argument("--root", type=Path, required=True)
    check.add_argument("--manifest", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    if args.command == "build":
        output = (args.output or root / "STANDALONE_MANIFEST.json").resolve()
        payload = build(root, args.kind, args.increment, args.wsl_root, output)
        print(json.dumps({"status": "BUILT", "identity": payload["identity"]}, ensure_ascii=False))
        return 0
    result = verify(root, (args.manifest or root / "STANDALONE_MANIFEST.json").resolve())
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
