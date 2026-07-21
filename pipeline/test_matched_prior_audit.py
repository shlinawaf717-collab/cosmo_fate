import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline import matched_prior_audit as m


def test_normalize_weights_simplex():
    w = m.normalize_weights(np.array([1.0, 2.0, 3.0]))
    assert np.isclose(w.sum(), 1.0)
    assert np.all(w >= 0)


def test_compute_deterministic():
    a = m.compute(n=1000, seed=7)
    b = m.compute(n=1000, seed=7)
    assert a == b


def test_low_ess_no_go_rejects():
    result = m.compute(n=1000, seed=8, min_ess_fraction=1.01, min_overlap=0.0)
    assert all(row["no_go"] for row in result["grammars"].values())
    assert all(row["matched_fate"] is None for row in result["grammars"].values())


def test_extreme_weight_truncation_improves_ess():
    rng = np.random.default_rng(1)
    samples = m.GrammarSamples("TOY", rng.normal(size=(500, len(m.SUMMARY_A))), np.array(["RIP"] * 500), "toy")
    target_mean = np.full(len(m.SUMMARY_A), 7.0)
    target_cov = np.eye(len(m.SUMMARY_A)) * 0.2
    _, diag = m.matched_weights(samples, target_mean, target_cov, 0.95)
    assert diag["ess_truncated"] >= diag["ess_raw"]
    assert diag["max_weight_truncated"] <= diag["max_weight_raw"]


def test_fate_probabilities_sum_to_one_when_go():
    result = m.compute(n=1200, seed=9, min_ess_fraction=0.0, min_overlap=0.0)
    for row in result["grammars"].values():
        assert np.isclose(sum(row["native_fate"].values()), 1.0)
        assert np.isclose(sum(row["matched_fate"].values()), 1.0)
