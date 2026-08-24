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
