import numpy as np
import pytest

from pipeline.wp5_formal_theory_gate import max_relative


def test_max_relative_respects_start_index():
    reference = np.asarray([0.0, 1.0, 2.0])
    candidate = np.asarray([10.0, 1.0, 2.002])
    assert max_relative(candidate, reference, start=1) == pytest.approx(0.001)
