import numpy as np

from pipeline.wp7_wp8_preflight import (
    admissible_winf_interval,
    build_preflight,
)


def test_registered_mild_boundary_states_admit_both_fate_sides():
    for tau in (0.5, 1.0, 2.0):
        interval = admissible_winf_interval(-0.9, 0.0, tau)
        assert interval is not None
        assert interval[0] < -1.0 < interval[1]


def test_admissible_interval_matches_direct_grid_bounds():
    w1, s1, tau = -0.9, 0.2, 1.0
    interval = admissible_winf_interval(w1, s1, tau)
    assert interval is not None
    x = np.linspace(0.0, np.log(1e6), 512)
    for w_inf in interval:
        a = w1 - w_inf
        b = s1 + a / tau
        values = w_inf + (a + b * x) * np.exp(-x / tau)
        assert np.min(values) >= -3.0 - 1e-10
        assert np.max(values) <= 1.0 + 1e-10


def test_out_of_bounds_boundary_state_has_no_admissible_continuation():
    assert admissible_winf_interval(-3.1, 0.0, 1.0) is None
    assert admissible_winf_interval(1.1, 0.0, 1.0) is None


def test_preflight_detects_ell_1p4_conditioning_and_spline_coupling():
    report = build_preflight()
    ell_1p4 = next(
        row for row in report["wp7_covariance"] if row["ell"] == 1.4
    )
    assert ell_1p4["condition_number"] > 1e8
    assert ell_1p4["numerical_status"] == "WARN_HIGH_CONDITION_NUMBER"
    leakage = report["wp7_spline_past_future_leakage"]
    assert leakage["status"] == "PAST_FUTURE_COUPLING_DETECTED"
    assert leakage["maximum_abs_response"] > 0.05
    assert all(
        abs(row["response_at_a1"]) < 1e-12 for row in leakage["responses"]
    )
    for source in report["inputs"].values():
        assert len(source["sha256"]) == 64
