import numpy as np

from pipeline.monitor_wp7 import _node_ess, rank_normalized_split_rhat


def test_two_chain_sbc_diagnostics_can_pass():
    rng = np.random.default_rng(2026090800)
    chains = [rng.normal(size=6000), rng.normal(size=6000)]
    assert rank_normalized_split_rhat(chains) < 1.01
    bulk, tail = _node_ess(chains)
    assert bulk > 400 and tail > 400
