from pathlib import Path

import numpy as np
import pytest

from pipeline.run_wp4_f1_bestfits import information_criteria, write_covmat


def test_f1_information_criteria_use_two_extra_parameters():
    result = information_criteria(-10.0, delta_k=2, nominal_n=100)
    assert result["delta_AIC"] == -6.0
    assert result["delta_BIC"] == pytest.approx(-10.0 + 2 * np.log(100))


def test_write_covmat_records_positive_metric(tmp_path: Path):
    target = tmp_path / "proposal.covmat"
    record = write_covmat(target, ["a", "b"], np.asarray([[2.0, 0.1], [0.1, 1.0]]))
    assert record["shape"] == [2, 2]
    assert record["minimum_eigenvalue"] > 0
