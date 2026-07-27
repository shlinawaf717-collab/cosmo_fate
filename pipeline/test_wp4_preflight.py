import json
from pathlib import Path

import numpy as np
import pytest

from pipeline.wp4_preflight import (
    REFERENCE_COLUMNS,
    WP4PreflightError,
    official_reference,
)


def _write_chain(path: Path, rows: list[list[float]]) -> None:
    columns = ["weight", "minuslogpost", *REFERENCE_COLUMNS.values()]
    with path.open("w", encoding="utf-8") as stream:
        stream.write("# " + " ".join(columns) + "\n")
        np.savetxt(stream, np.asarray(rows, dtype=float))


def test_official_reference_uses_posterior_weights(tmp_path):
    first = tmp_path / "chain.1.txt"
    second = tmp_path / "chain.2.txt"
    _write_chain(
        first,
        [
            [1, 10, -1.0, 0.0, 0.30, 68.0],
            [3, 11, -0.8, -0.4, 0.32, 66.0],
        ],
    )
    _write_chain(second, [[2, 12, -0.9, -0.2, 0.31, 67.0]])
    report = official_reference([first, second], expected_hashes={})
    values = np.asarray([-1.0, -0.8, -0.9])
    weights = np.asarray([1.0, 3.0, 2.0])
    expected_mean = float(np.average(values, weights=weights))
    expected_sd = float(
        np.sqrt(np.average((values - expected_mean) ** 2, weights=weights))
    )
    assert report["raw_rows"] == 3
    assert report["posterior_weight"] == 6
    assert report["parameters"]["w0"]["mean"] == pytest.approx(expected_mean)
    assert report["parameters"]["w0"]["sd"] == pytest.approx(expected_sd)


def test_official_reference_rejects_hash_mismatch(tmp_path):
    path = tmp_path / "chain.1.txt"
    _write_chain(path, [[1, 10, -1.0, 0.0, 0.30, 68.0]])
    with pytest.raises(WP4PreflightError, match="hash mismatch"):
        official_reference([path], expected_hashes={path.name: "0" * 64})


def test_official_reference_is_json_serializable(tmp_path):
    path = tmp_path / "chain.1.txt"
    _write_chain(path, [[1, 10, -1.0, 0.0, 0.30, 68.0]])
    json.dumps(official_reference([path], expected_hashes={}))
