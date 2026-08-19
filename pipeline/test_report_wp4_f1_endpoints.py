import numpy as np
import pytest

from pipeline.report_wp4_f1_endpoints import F1EndpointError, weighted_quantile


def test_weighted_quantile_respects_integer_mass():
    values = np.asarray([0.0, 10.0])
    weights = np.asarray([3.0, 1.0])
    q = weighted_quantile(values, weights, [0.5])
    assert q[0] == pytest.approx(2.5)


def test_weighted_quantile_rejects_nonpositive_weights():
    with pytest.raises(F1EndpointError, match="positive"):
        weighted_quantile(np.asarray([1.0, 2.0]), np.asarray([1.0, 0.0]), [0.5])
