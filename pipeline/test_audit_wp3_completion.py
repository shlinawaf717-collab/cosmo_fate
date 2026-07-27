import numpy as np

from pipeline.audit_wp3_completion import (
    _monotonicity,
    exact_interval,
    plus_one_upper_tail,
)


def test_plus_one_upper_tail_and_finite_floor():
    null = np.arange(500, dtype=float)
    deepest = plus_one_upper_tail(null, 500.0)
    assert deepest["null_count_greater_or_equal"] == 0
    assert deepest["p_plus_one"] == 1 / 501
    assert deepest["reject_at_alpha_0p05"] is True


def test_plus_one_alpha_boundary():
    null = np.arange(500, dtype=float)
    assert plus_one_upper_tail(null, 476.0)["p_plus_one"] == 25 / 501
    assert plus_one_upper_tail(null, 476.0)["reject_at_alpha_0p05"] is True
    assert plus_one_upper_tail(null, 475.0)["p_plus_one"] == 26 / 501
    assert plus_one_upper_tail(null, 475.0)["reject_at_alpha_0p05"] is False


def test_exact_interval_contains_point_estimate():
    low, high = exact_interval(80, 100)
    assert low < 0.8 < high


def test_monotonicity_only_triggers_for_disjoint_reversal():
    def point(rate, low, high):
        return {
            "direction_power": {
                "rate": rate,
                "exact_binomial_95_interval": [low, high],
            }
        }

    points = {
        "wam015": point(0.80, 0.70, 0.88),
        "wam030": point(0.79, 0.69, 0.87),
        "wam060": point(0.95, 0.89, 0.98),
        "wap015": point(0.80, 0.70, 0.88),
        "wap030": point(0.50, 0.40, 0.60),
        "wap060": point(0.90, 0.82, 0.95),
    }
    report = _monotonicity(points)
    assert report["negative_wa"][0]["point_estimate_reversal"] is True
    assert (
        report["negative_wa"][0]["reversal_beyond_binomial_uncertainty"]
        is False
    )
    assert report["positive_wa"][0]["reversal_beyond_binomial_uncertainty"] is True
    assert report["status"] == "DIAGNOSTIC_TRIGGERED"
