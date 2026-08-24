import hashlib
from pathlib import Path

import pytest

import pipeline.authorize_wp7_postprocessing as authorization


def _write_chain(path: Path):
    path.parent.mkdir(parents=True)
    path.write_text("# weight x\n1 0.0\n2 1.0\n", encoding="utf-8")


def test_chain_identity_matches_final_snapshot(monkeypatch, tmp_path):
    monkeypatch.setattr(authorization, "ROOT", tmp_path)
    path = tmp_path / "runs/chain.1.txt"
    _write_chain(path)
    expected = {
        "rows": 2,
        "captured_bytes": path.stat().st_size,
        "sha256": authorization.sha256_file(path),
        "total_weight": 3,
    }
    identity = authorization.chain_identity(path, expected)
    assert identity["path"] == "runs/chain.1.txt"
    assert identity["rows"] == 2
    assert identity["total_weight_at_final_stop"] == 3
    assert identity["post_audit_complete_rows_excluded"] == 0


def test_chain_identity_accepts_and_counts_an_append_only_suffix(monkeypatch, tmp_path):
    monkeypatch.setattr(authorization, "ROOT", tmp_path)
    path = tmp_path / "runs/chain.1.txt"
    _write_chain(path)
    captured = path.read_bytes()
    expected = {
        "rows": 2,
        "captured_bytes": len(captured),
        "sha256": hashlib.sha256(captured).hexdigest(),
        "total_weight": 3,
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write("1 2.0\n")
    identity = authorization.chain_identity(path, expected)
    assert identity["rows"] == 2
    assert identity["current_complete_rows"] == 3
    assert identity["post_audit_complete_rows_excluded"] == 1


def test_chain_identity_rejects_a_changed_chain(monkeypatch, tmp_path):
    monkeypatch.setattr(authorization, "ROOT", tmp_path)
    path = tmp_path / "runs/chain.1.txt"
    _write_chain(path)
    expected = {
        "rows": 2,
        "captured_bytes": path.stat().st_size,
        "sha256": "0" * 64,
        "total_weight": 3,
    }
    with pytest.raises(authorization.WP7AuthorizationError, match="sha256"):
        authorization.chain_identity(path, expected)
