import io
import json
import tarfile
from pathlib import Path

import pytest

from pipeline.ingest_wp4_f1_wsl2 import F1IngestError, sha256_bytes, verify_archive


def _archive(path: Path, files: dict[str, bytes], corrupt: bool = False) -> None:
    manifest = {
        "schema_version": "test",
        "files": [
            {"path": name, "bytes": len(data), "sha256": sha256_bytes(data)}
            for name, data in sorted(files.items())
        ],
    }
    with tarfile.open(path, "w:gz") as tar:
        for name, data in files.items():
            payload = (data + b"x") if corrupt and name == sorted(files)[0] else data
            info = tarfile.TarInfo(name); info.size = len(payload)
            tar.addfile(info, io.BytesIO(payload))
        raw = json.dumps(manifest).encode()
        info = tarfile.TarInfo("WSL2_RESULT_MANIFEST.json"); info.size = len(raw)
        tar.addfile(info, io.BytesIO(raw))


def test_verify_archive_checks_every_declared_file(tmp_path: Path):
    path = tmp_path / "result.tar.gz"
    _archive(path, {"work/a.json": b"{}", "work/chain.txt": b"# x\n1\n"})
    manifest, _ = verify_archive(path)
    assert len(manifest["files"]) == 2


def test_verify_archive_rejects_hash_mismatch(tmp_path: Path):
    path = tmp_path / "result.tar.gz"
    _archive(path, {"work/a.json": b"{}"}, corrupt=True)
    with pytest.raises(F1IngestError, match="hash mismatch"):
        verify_archive(path)
