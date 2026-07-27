import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "plan/wp8_future_continuation_protocol.json"
PROTOCOL = ROOT / "plan/WP8_FUTURE_CONTINUATION_PROTOCOL.md"
AMENDMENTS = ROOT / "plan/PRD_EXTENSION_AMENDMENTS.md"


def load_spec():
    return json.loads(SPEC.read_text(encoding="utf-8"))


def test_wp8_is_separate_prospective_protocol():
    spec = load_spec()
    assert spec["schema_version"] == "wp8-future-continuation-v1"
    assert spec["parent_amendment"] == "PRD-A005"
    assert spec["requires"]["wp7_primary_converged"] is True
    assert spec["requires"]["source_domain_max_a"] == 1.0
    assert spec["results_root"].startswith("runs/prd_extension/")
    assert PROTOCOL.is_file()
    assert "PRD-A005" in AMENDMENTS.read_text(encoding="utf-8")


def test_registered_smooth_formula_matches_boundary_and_asymptote():
    w1 = -0.83
    s1 = 0.17
    w_inf = -1.12
    for tau in (0.5, 1.0, 2.0):
        A = w1 - w_inf
        B = s1 + A / tau

        def w(x):
            return w_inf + (A + B * x) * np.exp(-x / tau)

        np.testing.assert_allclose(w(0.0), w1, rtol=0.0, atol=1e-15)
        step = 1e-6
        derivative = (w(step) - w(-step)) / (2.0 * step)
        np.testing.assert_allclose(derivative, s1, rtol=0.0, atol=1e-9)
        assert abs(w(100.0) - w_inf) < 1e-12


def test_families_and_sensitivities_cannot_be_selected_post_result():
    spec = load_spec()
    families = {row["id"]: row for row in spec["families"]}
    assert set(families) == {"C0", "C1", "C2", "C3"}
    assert families["C2"]["tau_values"] == [0.5, 1.0, 2.0]
    assert families["C3"]["tau_values"] == [0.5, 1.0, 2.0]
    assert spec["family_model_averaging"] is False
    assert spec["monte_carlo"]["optional_stopping"] is False
    assert spec["monte_carlo"]["replicates"] == [1, 2]


def test_interpretation_gate_forbids_unqualified_fate_when_span_is_large():
    gate = load_spec()["interpretation_gate"]
    assert gate["max_unqualified_P_RIP_span"] == 0.1
    assert gate["max_unqualified_P_heat_span"] == 0.1
    assert gate["min_unqualified_robust_side_fraction"] == 0.9
    assert "prohibit a single continuation-unqualified fate probability" in gate[
        "failure_action"
    ]


def test_future_asymptote_is_likelihood_independent_and_bounded():
    spec = load_spec()
    c3 = next(row for row in spec["families"] if row["id"] == "C3")
    assert c3["w_inf_likelihood_independent"] is True
    assert c3["w_inf_distribution"]["truncated_bounds"] == [-3.0, 1.0]
    assert spec["function_admissibility"]["grid_a"] == [1.0, 1_000_000.0]
    assert spec["validation"]["past_loglike_absolute_tolerance"] == 1e-8
