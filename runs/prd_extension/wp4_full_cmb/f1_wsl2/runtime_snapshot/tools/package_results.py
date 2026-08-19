#!/usr/bin/env python3
"""Create a content-hashed return archive containing WSL2 F1 runtime products."""

from __future__ import annotations

import hashlib
import json
import tarfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "work"


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024*1024), b""): digest.update(block)
    return digest.hexdigest()


def main() -> int:
    records = []
    for path in sorted(x for x in WORK.rglob("*") if x.is_file()):
        records.append({"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size, "sha256": sha(path)})
    manifest = ROOT / "WSL2_RESULT_MANIFEST.json"
    manifest.write_text(json.dumps({"schema_version": "wp4-f1-wsl2-return-v1", "created_at_utc": datetime.now(timezone.utc).isoformat(), "files": records}, indent=2, sort_keys=True) + "\n")
    archive = ROOT / "WP4_F1_WSL2_RESULTS.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(WORK, arcname="work"); tar.add(manifest, arcname=manifest.name)
    checksum = ROOT / "WP4_F1_WSL2_RESULTS.tar.gz.sha256"
    checksum.write_text(f"{sha(archive)}  {archive.name}\n")
    print(json.dumps({"archive": str(archive), "bytes": archive.stat().st_size, "sha256": sha(archive)}))
    return 0


if __name__ == "__main__": raise SystemExit(main())
