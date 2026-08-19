import numpy as np

from pipeline.monitor_wp7 import _hidden_sign_mcse_pass, _node_ess, rank_normalized_split_rhat


def test_rank_rhat_and_ess_pass_for_mixed_iid_chains():
    rng = np.random.default_rng(2026090700)
    chains = [rng.normal(size=5000) for _ in range(4)]
    assert rank_normalized_split_rhat(chains) < 1.01
    bulk, tail = _node_ess(chains)
    assert bulk > 400 and tail > 400
    shifted = list(chains); shifted[0] = shifted[0] + 1.0
    assert rank_normalized_split_rhat(shifted) > 1.01


def test_hidden_sign_mcse_returns_only_boolean_gate():
    rng = np.random.default_rng(2026090701)
    chains = [rng.normal(loc=-1.0, scale=0.3, size=10000) for _ in range(4)]
    result = _hidden_sign_mcse_pass(chains)
    assert isinstance(result, bool)
    assert result
