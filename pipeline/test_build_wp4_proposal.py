from pathlib import Path

import numpy as np

from pipeline.build_wp4_proposal import proposal_covariance


def _write_chain(path: Path, rows: np.ndarray) -> None:
    with path.open("w", encoding="utf-8") as stream:
        stream.write("# weight minuslogpost x y\n")
        np.savetxt(stream, rows)


def test_proposal_covariance_uses_weights_and_is_positive_definite(tmp_path):
    path = tmp_path / "chain.1.txt"
    rows = np.asarray(
        [
            [1, 10, 0.0, 0.0],
            [2, 11, 1.0, 0.0],
            [1, 12, 0.0, 2.0],
            [2, 13, 2.0, 1.0],
        ],
        dtype=float,
    )
    _write_chain(path, rows)
    covariance, audit = proposal_covariance(
        [path],
        parameters=["x", "y"],
        expected_hashes={},
    )
    expected = np.cov(rows[:, 2:].T, aweights=rows[:, 0], ddof=0)
    assert np.allclose(covariance, expected)
    np.linalg.cholesky(covariance)
    assert audit["status"] == "PASS"
    assert audit["posterior_weight"] == 6
