import numpy as np

from pipeline.wp7_fs7 import spline
from pipeline.wp8_future_continuation import (
    GRID_X,
    admissible_winf_interval,
    boundary_derivative,
    c3_seed,
    continuation_derivative,
    continuation_values,
    direct_admissible,
    draw_c3_asymptotes,
    support_categories,
    systematic_weighted_indices,
)


def test_boundary_derivative_matches_registered_spline_exactly():
    rows = np.array(
        [
            [-1.2, -1.1, -1.0, -0.9, -0.8, -0.7, -0.6],
            [-0.7, -1.3, -0.8, -1.2, -0.9, -1.1, -1.0],
        ]
    )
    expected = np.array([spline(row)(0.0, 1) for row in rows])
    np.testing.assert_allclose(boundary_derivative(rows), expected, rtol=0, atol=1e-14)


def test_registered_continuation_matches_value_derivative_and_asymptote():
    w1 = np.array([-1.2, -0.8])
    s1 = np.array([0.3, -0.2])
    w_inf = np.array([-1.4, -0.6])
    for tau in (0.5, 1.0, 2.0):
        np.testing.assert_allclose(
            continuation_values(w1, s1, w_inf, tau, 0.0), w1, rtol=0, atol=1e-15
        )
        np.testing.assert_allclose(
            continuation_derivative(w1, s1, w_inf, tau, 0.0), s1, rtol=0, atol=1e-15
        )
        np.testing.assert_allclose(
            continuation_values(w1, s1, w_inf, tau, 100.0),
            w_inf,
            rtol=0,
            atol=1e-14,
        )


def test_analytic_interval_is_equivalent_to_direct_512_grid():
    rng = np.random.default_rng(9374)
    w1 = rng.uniform(-2.8, 0.8, 80)
    s1 = rng.uniform(-2.0, 2.0, 80)
    probes = rng.uniform(-3.0, 1.0, (80, 31))
    for tau in (0.5, 1.0, 2.0):
        lower, upper, valid = admissible_winf_interval(w1, s1, tau)
        analytic = valid[:, None] & (probes >= lower[:, None]) & (probes <= upper[:, None])
        direct = direct_admissible(
            np.repeat(w1, probes.shape[1]),
            np.repeat(s1, probes.shape[1]),
            probes.ravel(),
            tau,
        ).reshape(probes.shape)
        np.testing.assert_array_equal(analytic, direct)


def test_interval_extrema_obey_registered_grid_bounds():
    w1 = np.array([-1.1, -1.0, -0.9])
    s1 = np.array([-0.2, 0.0, 0.2])
    for tau in (0.5, 1.0, 2.0):
        lower, upper, valid = admissible_winf_interval(w1, s1, tau)
        assert np.all(valid)
        assert np.all(direct_admissible(w1, s1, lower, tau, grid_x=GRID_X))
        assert np.all(direct_admissible(w1, s1, upper, tau, grid_x=GRID_X))


def test_systematic_weighted_indices_use_registered_midpoints():
    indices = systematic_weighted_indices(np.array([1, 2, 1]), 8)
    np.testing.assert_array_equal(indices, [0, 0, 1, 1, 1, 1, 2, 2])


def test_c3_sampler_is_bounded_symmetric_and_exactly_replayable():
    seed = c3_seed(1.0, 2)
    first = draw_c3_asymptotes(100_000, seed)
    second = draw_c3_asymptotes(100_000, seed)
    np.testing.assert_array_equal(first, second)
    assert np.all((-3.0 <= first) & (first <= 1.0))
    assert abs(np.mean(first) + 1.0) < 0.005
    assert abs(np.mean(first < -1.0) - 0.5) < 0.005


def test_partial_identification_categories_are_support_unions():
    c0 = np.array([-1.2, -0.8, -1.2, -0.8])
    c2 = [np.array([False, False, True, True])]
    interval = (
        np.array([-2.0, -0.8, -2.0, -0.8]),
        np.array([-1.1, 0.5, 0.5, 0.5]),
        np.ones(4, dtype=bool),
    )
    result = support_categories(c0, c2, [interval])
    np.testing.assert_array_equal(result, ["{RIP}", "{heat}", "{RIP,heat}", "{heat}"])
