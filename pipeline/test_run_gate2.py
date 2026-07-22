import json
from pathlib import Path

import pytest

from pipeline import run_gate2


def make_mock_inputs(mock_root: Path, *indices: int) -> None:
    mock_root.mkdir(parents=True)
    (mock_root / "mocks_manifest.json").write_text(
        json.dumps({"seed": 42, "n": max(indices)}), encoding="utf-8"
    )
    for k in indices:
        mock_dir = mock_root / f"m{k:03d}"
        mock_dir.mkdir()
        for name in run_gate2.REQUIRED_MOCK_INPUTS:
            payload = '{"mean": [1, 2, 3]}' if name == "cmb_mean.json" else "fixture\n"
            (mock_dir / name).write_text(payload, encoding="utf-8")


def test_default_campaign_is_isolated_null500():
    paths = run_gate2.RunPaths.from_root(run_gate2.DEFAULT_RUN_ROOT)
    assert paths.run_root == run_gate2.ROOT / "runs" / "prd_extension" / "null500"
    assert paths.mocks == paths.run_root / "mocks"
    assert paths.results == paths.run_root / "results.jsonl"


@pytest.mark.parametrize(
    "unsafe",
    ["runs/gate2", "runs/phase2", "runs/phase3", "runs/prd_extension"],
)
def test_cli_root_guard_rejects_v1x_and_unnamed_extension_root(unsafe):
    with pytest.raises(ValueError, match="refusing|named directory"):
        run_gate2.require_extension_run_root(unsafe)


def test_root_guard_rejects_symlink_escape(tmp_path, monkeypatch):
    extension = tmp_path / "runs" / "prd_extension"
    outside = tmp_path / "outside"
    extension.mkdir(parents=True)
    outside.mkdir()
    (extension / "escape").symlink_to(outside, target_is_directory=True)
    monkeypatch.setattr(run_gate2, "EXTENSION_RESULTS_ROOT", extension)
    with pytest.raises(ValueError, match="outside"):
        run_gate2.require_extension_run_root(extension / "escape")


def test_resume_ledger_is_campaign_local(tmp_path):
    extension = run_gate2.RunPaths.from_root(tmp_path / "null500")
    legacy = tmp_path / "gate2" / "results.jsonl"
    extension.run_root.mkdir()
    legacy.parent.mkdir()
    extension.results.write_text('{"k": 101}\n', encoding="utf-8")
    legacy.write_text('{"k": 102}\n', encoding="utf-8")
    assert run_gate2.done_ks(extension.results) == {101}
    assert run_gate2.pending_ks(extension, 101, 102) == [102]


def test_preflight_fails_before_any_production_write(tmp_path):
    paths = run_gate2.RunPaths.from_root(tmp_path / "null500")
    make_mock_inputs(paths.mocks, 101)
    (paths.mocks / "m101" / "bao_cov.txt").unlink()
    with pytest.raises(FileNotFoundError, match="bao_cov.txt"):
        run_gate2.preflight(paths, [101])
    assert not (paths.mocks / "m101" / "run.yaml").exists()
    assert not paths.results.exists()


def test_preflight_rejects_mock_directory_symlink_escape(tmp_path):
    paths = run_gate2.RunPaths.from_root(tmp_path / "null500")
    paths.mocks.mkdir(parents=True)
    (paths.mocks / "mocks_manifest.json").write_text("{}\n", encoding="utf-8")
    outside = tmp_path / "legacy-mock"
    outside.mkdir()
    (paths.mocks / "m101").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="mock directory escapes"):
        run_gate2.preflight(paths, [101])


def test_make_yaml_keeps_all_mutable_outputs_in_campaign(tmp_path):
    paths = run_gate2.RunPaths.from_root(tmp_path / "null500")
    make_mock_inputs(paths.mocks, 101)
    mock_dir, yaml_path = run_gate2.make_yaml(101, paths)
    text = yaml_path.read_text(encoding="utf-8")
    assert mock_dir == paths.mocks / "m101"
    assert yaml_path == mock_dir / "run.yaml"
    assert str(mock_dir / "chain") in text
    assert str(run_gate2.ROOT / "runs" / "gate2") not in text


def test_dry_run_writes_nothing_and_skips_completed(tmp_path, monkeypatch):
    extension = tmp_path / "runs" / "prd_extension"
    run_root = extension / "null500"
    paths = run_gate2.RunPaths.from_root(run_root)
    make_mock_inputs(paths.mocks, 101, 102)
    paths.results.write_text('{"k": 101}\n', encoding="utf-8")
    before = paths.results.read_bytes()
    monkeypatch.setattr(run_gate2, "EXTENSION_RESULTS_ROOT", extension)
    selected = run_gate2.main(101, 102, jobs=1, run_root=run_root, dry_run=True)
    assert selected == [102]
    assert paths.results.read_bytes() == before
    assert not (paths.mocks / "m101" / "run.yaml").exists()
    assert not (paths.mocks / "m102" / "run.yaml").exists()


def test_cli_defaults_target_only_new_wp2_indices():
    args = run_gate2.parse_args([])
    assert (args.k_start, args.k_end, args.jobs) == (101, 500, 4)
    assert args.run_root == "runs/prd_extension/null500"


def test_range_guard_matches_frozen_wp2_bounds():
    run_gate2.validate_range(1, 500, 1)
    for values in ((0, 500, 1), (1, 501, 1), (10, 9, 1), (1, 500, 0)):
        with pytest.raises(ValueError):
            run_gate2.validate_range(*values)
