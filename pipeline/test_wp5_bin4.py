import numpy as np
import pytest

from pipeline.wp5_bin4 import (
    PRIMARY_DELTA_LNA,
    TRANSITION_A,
    WP5Bin4Error,
    make_bin4_ppf,
    make_bin4_table,
    make_cpl_table,
    smooth_bin4_w,
)


def test_smooth_bin4_has_registered_order_and_midpoints():
    values = (-0.8, -1.0, -1.2, -1.4)
    probes = np.asarray([1e-4, 0.45, 0.65, 0.9])
    result = smooth_bin4_w(probes, values, delta_lna=0.005)
    assert result == pytest.approx(values[::-1], abs=2e-5)
    ordered = values[::-1]
    for edge, left, right in zip(TRANSITION_A, ordered[:-1], ordered[1:]):
        assert smooth_bin4_w(edge, values, delta_lna=PRIMARY_DELTA_LNA) == pytest.approx(
            0.5 * (left + right), abs=2e-11
        )


def test_equal_bins_are_exactly_constant_and_table_ends_at_one():
    a, w = make_bin4_table(-0.9, -0.9, -0.9, -0.9)
    assert np.all(np.diff(a) > 0)
    assert a[-1] == 1.0
    assert np.max(np.abs(w + 0.9)) < 1e-14


def test_cpl_table_reproduces_analytic_values():
    a, w = make_cpl_table(-0.85, -0.6)
    assert w == pytest.approx(-0.85 - 0.6 * (1 - a), abs=1e-14)


def test_ppf_accepts_crossing_table():
    model = make_bin4_ppf(-0.8, -1.2, -0.9, -1.1)
    assert model.use_tabulated_w


def test_invalid_bin_or_grid_is_rejected():
    with pytest.raises(WP5Bin4Error):
        smooth_bin4_w(1.0, (-1, -1, -1, 2), 0.01)
    with pytest.raises(WP5Bin4Error):
        make_bin4_table(-1, -1, -1, -1, a_min=0)
