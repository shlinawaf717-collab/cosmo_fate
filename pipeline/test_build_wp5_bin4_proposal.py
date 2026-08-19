import numpy as np

from pipeline.build_wp5_bin4_proposal import PARAMETERS, SHARED, W_BINS


def test_wp5_proposal_parameter_partition_is_complete():
    assert len(PARAMETERS) == 20
    assert set(SHARED).isdisjoint(W_BINS)
    assert set(SHARED).union(W_BINS) == set(PARAMETERS)


def test_wp5_proposal_bin_order_is_registered():
    assert W_BINS == ("w1", "w2", "w3", "w4")
