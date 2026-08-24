import math

import numpy as np

from pipeline.report_wp7 import (
    _classify_posterior,
    _sign_batch_mcse,
    quantile_bin_kl,
    weighted_summary,
)


def test_weighted_summary_uses_registered_inverted_cdf():
    result = weighted_summary(np.array([0.0, 1.0, 2.0]), np.array([1, 2, 1]))
    assert result["mean"] == 1.0
    assert result["population_sd"] == math.sqrt(0.5)
    assert result["quantiles"]["0.025"] == 0.0
    assert result["quantiles"]["0.5"] == 1.0
    assert result["quantiles"]["0.975"] == 2.0


def test_quantile_bin_kl_is_zero_for_uniform_mass_and_conserves_outer_tails():
    edges = [0.0, 1.0, 2.0, 3.0, 4.0]
    uniform = quantile_bin_kl(
        np.array([-100.0, 1.5, 2.5, 100.0]), np.ones(4), edges
    )
    assert uniform["posterior_mass_conserved"] is True
    assert abs(uniform["kl_nats"]) < 1.0e-15
    concentrated = quantile_bin_kl(np.array([0.5, 0.6]), np.ones(2), edges)
    assert concentrated["kl_nats"] == math.log(4.0)


def test_hidden_sign_mcse_matches_balanced_synthetic_batches():
    values = np.tile(np.array([-1.2, -0.8]), 320)
    nodes = np.full((len(values), 7), -1.0)
    nodes[:, -1] = values
    chains = [{"nodes": nodes.copy(), "weights": np.ones(len(values), dtype=int)} for _ in range(4)]
    result = _sign_batch_mcse(chains)
    assert result["mcse"] == 0.0
    assert result["total_batches"] == 128
    assert result["passes_registered_0p01_gate"] is True


def test_finite_limit_fate_labels_and_boundary_are_separate():
    nodes = np.full((3, 7), -1.0)
    nodes[:, -1] = [-1.2, -1.0, -0.8]
    result = _classify_posterior(
        nodes,
        np.full(3, 0.3),
        np.full(3, 70.0),
        np.ones(3),
    )
    assert result["fractions"]["RIP"] == 1 / 3
    assert result["fractions"]["DS"] == 1 / 3
    assert result["fractions"]["DECAY"] == 1 / 3
    assert result["fractions"]["BOUNDARY"] == 1 / 3
    assert result["fractions"]["OTHER"] == 0.0
