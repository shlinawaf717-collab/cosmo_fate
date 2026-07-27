import json
import os
from pathlib import Path

import pytest

from pipeline import migrate_null500


def build_fixture(tmp_path: Path, expected_noisy: int = 1):
    source_root = tmp_path / "source"
    source_mocks = source_root / "mocks"
    source_mocks.mkdir(parents=True)
    cov_root = tmp_path / "shared"
    cov_root.mkdir()
    sn_cov = cov_root / "sn.cov"
    bao_cov = cov_root / "bao.txt"
    sn_cov.write_text("sn covariance\n", encoding="utf-8")
    bao_cov.write_text("bao covariance\n", encoding="utf-8")
    covariances = {"sn_cov.cov": sn_cov, "bao_cov.txt": bao_cov}

    manifest = {"seed": 42, "n": expected_noisy, "truth": {"H0": 70.0}}
    (source_mocks / "mocks_manifest.json").write_text(
        json.dumps(manifest) + "\n", encoding="utf-8"
    )
    for k in range(expected_noisy + 1):
        mock_dir = source_mocks / f"m{k:03d}"
        mock_dir.mkdir()
        for name in migrate_null500.REQUIRED_SOURCE_FILES:
            (mock_dir / name).write_text(f"{name} mock {k}\n", encoding="utf-8")
        for name, canonical in covariances.items():
            (mock_dir / name).symlink_to(canonical.resolve())

    source_results = source_root / "results.jsonl"
    source_results.write_text(
        "".join(json.dumps({"k": k, "P": {"RIP": 0.1 * k}}) + "\n"
                for k in range(expected_noisy + 1)),
        encoding="utf-8",
    )
    source_truth = source_root / "truth.json"
    source_truth.write_text('{"H0": 70.0}\n', encoding="utf-8")
    target = tmp_path / "runs" / "prd_extension" / "null500"
    return source_mocks, source_results, source_truth, target, covariances


def migrate_fixture(tmp_path: Path, **kwargs):
    source_mocks, source_results, source_truth, target, covariances = build_fixture(tmp_path)
    report = migrate_null500.migrate(
        source_mocks=source_mocks,
        source_results=source_results,
        source_truth=source_truth,
        target_root=target,
        covariances=covariances,
        expected_noisy=1,
        verify_git=False,
        **kwargs,
    )
    return source_mocks, source_results, source_truth, target, covariances, report


def test_dry_run_validates_without_writing(tmp_path):
    source_mocks, _, _, target, _, report = migrate_fixture(tmp_path, dry_run=True)
    assert report["mock_directories"] == 2
    assert report["result_rows"] == 2
    assert report["dry_run"] is True
    assert not target.exists()
    assert Path(os.readlink(source_mocks / "m000" / "sn_cov.cov")).is_absolute()


def test_migration_is_atomic_byte_preserving_and_repairs_links(tmp_path):
    source_mocks, source_results, source_truth, target, covariances, report = migrate_fixture(
        tmp_path
    )
    assert target.is_dir()
    assert report["validation"] == {
        "source_unchanged": True,
        "regular_files_byte_identical": True,
        "result_indices_complete_and_unique": True,
        "covariance_links_relative_and_resolved": True,
        "atomic_publish": True,
    }
    assert (target / "results.jsonl").read_bytes() == source_results.read_bytes()
    assert (target / "truth_lcdm_d0.json").read_bytes() == source_truth.read_bytes()
    for k in range(2):
        for name, canonical in covariances.items():
            source_link = source_mocks / f"m{k:03d}" / name
            target_link = target / "mocks" / f"m{k:03d}" / name
            assert Path(os.readlink(source_link)).is_absolute()
            assert not Path(os.readlink(target_link)).is_absolute()
            assert target_link.resolve() == canonical.resolve()
    manifest = json.loads((target / "migration_manifest.json").read_text())
    inventory = json.loads((target / "migration_inventory.json").read_text())
    assert manifest["inventory"]["entries"] == len(inventory)
    assert manifest["source"]["regular_tree_sha256"] == manifest["target"]["regular_tree_sha256"]
    audit = migrate_null500.audit_target(target, covariances, expected_noisy=1)
    assert audit["audit"] == "PASS"
    assert audit["relative_covariance_links"] == 4


def test_existing_target_is_never_overwritten(tmp_path):
    source_mocks, source_results, source_truth, target, covariances = build_fixture(tmp_path)
    target.mkdir(parents=True)
    sentinel = target / "sentinel"
    sentinel.write_text("keep\n")
    with pytest.raises(migrate_null500.MigrationError, match="refusing to overwrite"):
        migrate_null500.migrate(
            source_mocks, source_results, source_truth, target, covariances,
            expected_noisy=1, verify_git=False
        )
    assert sentinel.read_text() == "keep\n"


def test_failure_removes_staging_and_leaves_no_partial_target(tmp_path, monkeypatch):
    source_mocks, source_results, source_truth, target, covariances = build_fixture(tmp_path)

    def fail(*args, **kwargs):
        raise RuntimeError("simulated link failure")

    monkeypatch.setattr(migrate_null500, "rewrite_covariance_links", fail)
    with pytest.raises(RuntimeError, match="simulated"):
        migrate_null500.migrate(
            source_mocks, source_results, source_truth, target, covariances,
            expected_noisy=1, verify_git=False
        )
    assert not target.exists()
    assert not list(target.parent.glob(".null500.migration-*"))


def test_incomplete_or_misdirected_source_fails_closed(tmp_path):
    source_mocks, source_results, source_truth, target, covariances = build_fixture(tmp_path)
    (source_mocks / "m001" / "chain.1.txt").unlink()
    with pytest.raises(migrate_null500.MigrationError, match="incomplete"):
        migrate_null500.migrate(
            source_mocks, source_results, source_truth, target, covariances,
            expected_noisy=1, verify_git=False, dry_run=True
        )


def test_audit_detects_post_migration_tampering(tmp_path):
    _, _, _, target, covariances, _ = migrate_fixture(tmp_path)
    (target / "mocks" / "m001" / "chain.1.txt").write_text("tampered\n")
    with pytest.raises(migrate_null500.MigrationError, match="inventory"):
        migrate_null500.audit_target(target, covariances, expected_noisy=1)


def test_audit_allows_declared_append_while_preserving_migration(tmp_path):
    _, _, _, target, covariances, _ = migrate_fixture(tmp_path)
    manifest_path = target / "mocks" / "mocks_manifest.json"
    mock_manifest = json.loads(manifest_path.read_text())
    mock_manifest.update(n=2, previous_n=1, append_range=[2, 2])
    manifest_path.write_text(json.dumps(mock_manifest) + "\n", encoding="utf-8")
    (target / "mocks" / "m002").mkdir()
    with (target / "results.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps({"k": 2, "P": {"RIP": 0.2}}) + "\n")

    audit = migrate_null500.audit_target(target, covariances, expected_noisy=1)

    assert audit["audit"] == "PASS"
    assert audit["mock_manifest_n"] == 2
    assert audit["baseline_result_rows"] == 2
    assert audit["result_rows"] == 3


def test_audit_rejects_append_that_changes_frozen_truth(tmp_path):
    _, _, _, target, covariances, _ = migrate_fixture(tmp_path)
    manifest_path = target / "mocks" / "mocks_manifest.json"
    mock_manifest = json.loads(manifest_path.read_text())
    mock_manifest.update(n=2, previous_n=1, append_range=[2, 2])
    mock_manifest["truth"] = {"H0": 71.0}
    manifest_path.write_text(json.dumps(mock_manifest) + "\n", encoding="utf-8")

    with pytest.raises(migrate_null500.MigrationError, match="frozen migration metadata"):
        migrate_null500.audit_target(target, covariances, expected_noisy=1)
