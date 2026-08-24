import hashlib

import pipeline.authorize_wp8 as authorizer


def test_chain_identity_accepts_only_the_frozen_complete_prefix(monkeypatch, tmp_path):
    monkeypatch.setattr(authorizer, "ROOT", tmp_path)
    path = tmp_path / "runs/source.txt"
    path.parent.mkdir(parents=True)
    prefix = b"# weight fs7_w1\n1 -1.0\n2 -0.9\n"
    path.write_bytes(prefix + b"3 -0.8\n")
    record = {
        "path": "runs/source.txt",
        "captured_bytes": len(prefix),
        "rows": 2,
        "sha256": hashlib.sha256(prefix).hexdigest(),
        "post_audit_complete_rows_excluded": 1,
    }
    result = authorizer._chain_identity(record)
    assert result["rows"] == 2
    assert result["sha256"] == record["sha256"]
    assert result["post_audit_complete_rows_excluded"] == 1


def test_chain_identity_rejects_mutated_prefix(monkeypatch, tmp_path):
    monkeypatch.setattr(authorizer, "ROOT", tmp_path)
    path = tmp_path / "runs/source.txt"
    path.parent.mkdir(parents=True)
    prefix = b"# weight fs7_w1\n1 -1.0\n"
    path.write_bytes(prefix)
    record = {
        "path": "runs/source.txt",
        "captured_bytes": len(prefix),
        "rows": 1,
        "sha256": "0" * 64,
        "post_audit_complete_rows_excluded": 0,
    }
    try:
        authorizer._chain_identity(record)
    except authorizer.WP8AuthorizationError as exc:
        assert "sha256 mismatch" in str(exc)
    else:
        raise AssertionError("mutated source prefix was accepted")
