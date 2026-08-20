import numpy as np

from pipeline.report_wp7_sbc import exact_acceptance_interval, holm_rejections, systematic_resample


def test_systematic_resample_is_deterministic_and_weighted():
    values = np.arange(6.0)[:, None]; weights = np.asarray([1, 1, 1, 1, 1, 20])
    first = systematic_resample(values, weights, 400, 123)
    second = systematic_resample(values, weights, 400, 123)
    np.testing.assert_array_equal(first, second)
    assert np.mean(first[:, 0] == 5.0) > 0.7


def test_holm_stops_after_first_nonrejection():
    result = holm_rejections({"a": 0.001, "b": 0.02, "c": 0.9}, alpha=0.05)
    assert result == {"a": True, "b": True, "c": False}


def test_exact_coverage_acceptance_intervals_are_ordered():
    for probability in (0.5, 0.9):
        lower, upper = exact_acceptance_interval(50, probability)
        assert 0 <= lower <= 50 * probability <= upper <= 50
