from pathlib import Path

import numpy as np

from pipeline.run_wp4_f0_bestfits import _read_covmat, write_subcovmat


def test_write_subcovmat_removes_dark_energy_parameters(tmp_path: Path):
    source = tmp_path / "source.covmat"
    target = tmp_path / "target.covmat"
    matrix = np.asarray([[4.0, 1.0, 0.0], [1.0, 3.0, 0.5], [0.0, 0.5, 2.0]])
    np.savetxt(source, matrix, header="x w wa")
    record = write_subcovmat(source, target, {"w", "wa"})
    names, result = _read_covmat(target)
    assert names == ["x"]
    assert result.shape == (1, 1)
    assert result[0, 0] == 4.0
    assert record["shape"] == [1, 1]
