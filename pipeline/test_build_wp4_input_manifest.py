from pathlib import Path

import pytest

from pipeline.build_wp4_input_manifest import (
    WP4InputManifestError,
    build_manifest,
)


def test_manifest_is_deterministic_and_detects_content_change(tmp_path):
    root = tmp_path / "inputs"
    root.mkdir()
    first = root / "a.dat"
    second = root / "b.dat"
    first.write_text("alpha\n", encoding="utf-8")
    second.write_text("beta\n", encoding="utf-8")
    groups = {"test": [root]}
    before = build_manifest(groups)
    repeated = build_manifest(groups)
    assert before["totals"]["tree_sha256"] == repeated["totals"]["tree_sha256"]
    assert before["totals"]["unique_file_count"] == 2

    second.write_text("changed\n", encoding="utf-8")
    after = build_manifest(groups)
    assert before["totals"]["tree_sha256"] != after["totals"]["tree_sha256"]


def test_manifest_rejects_missing_input(tmp_path):
    with pytest.raises(WP4InputManifestError, match="missing WP4 input"):
        build_manifest({"missing": [tmp_path / "absent"]})
