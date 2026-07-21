import pytest

from pipeline.fragility_audit import log_span


def test_finite_log_span():
    rows = [{"name": "a", "P": 1e-3}, {"name": "b", "P": 1e-1}]
    out = log_span(rows, "P")
    assert out["status"] == "finite"
    assert out["log10_span_dex"] == pytest.approx(2.0)


def test_structural_and_sampling_zeros_are_distinct():
    exact = [
        {"name": "a", "P": 0.1},
        {"name": "b", "P": 0.0, "P_zero_kind": "structural_prior"},
    ]
    sampled = [
        {"name": "a", "P": 0.1},
        {"name": "b", "P": 0.0, "P_zero_kind": "finite_nested_sampling"},
    ]
    assert log_span(exact, "P")["status"] == "structurally_unbounded_by_exact_zero"
    assert log_span(sampled, "P")["status"] == "finite_nested_sampling_zero_requires_limit_or_more_runs"
