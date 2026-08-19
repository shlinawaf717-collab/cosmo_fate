import numpy as np
import pytest

from pipeline.wp5_development_preflight import exact_piecewise_ln_fde


def test_exact_piecewise_density_is_continuous_and_constant_limit():
    z = np.asarray([0.0, 0.3, 0.7, 1.5, 10.0])
    result = exact_piecewise_ln_fde(z, np.asarray([-1.0, -1.0, -1.0, -1.0]))
    assert result == pytest.approx(np.zeros_like(z), abs=1e-15)


def test_exact_piecewise_uses_high_redshift_bin_above_last_transition():
    z = np.asarray([1.5, 3.0])
    result = exact_piecewise_ln_fde(z, np.asarray([-1.0, -1.0, -1.0, -0.5]))
    assert result[0] == pytest.approx(0.0)
    assert result[1] == pytest.approx(3 * 0.5 * np.log(4.0 / 2.5))
