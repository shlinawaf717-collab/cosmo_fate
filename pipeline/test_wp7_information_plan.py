import numpy as np

from pipeline.wp7_information_plan import _quantile_edges, _likelihood_window_response


def test_prior_quantile_edges_are_strict_and_complete():
    edges = _quantile_edges(np.linspace(-2.0, 2.0, 1001), 40)
    assert len(edges) == 41
    assert np.all(np.diff(edges) > 0)


def test_likelihood_window_response_labels_future_leakage():
    result = _likelihood_window_response()
    assert len(result["future_node_responses"]) == 3
    assert result["spline_basis_max_abs_over_a_le_1"]["fs7_w5"] > 0.05
    assert "not observation" in result["interpretation"]
