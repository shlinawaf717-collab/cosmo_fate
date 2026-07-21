import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline import matched_prior_audit as m


def test_declared_support_dimensions_and_common_intersection():
    assert {name: m.intrinsic_dimension(name) for name in m.GRAMMARS} == {
        "CPL": 2,
        "JBP": 2,
        "BA": 2,
        "BIN4": 3,
    }
    assert m.common_support_dimension() == 1
    constant = np.ones(len(m.SUMMARY_A))
    for name in m.GRAMMARS:
        coeff, *_ = np.linalg.lstsq(m.support_basis(name), constant, rcond=None)
        assert np.allclose(m.support_basis(name) @ coeff, constant)


def test_bin4_summary_uses_production_grid_mapping():
    basis = m.support_basis("BIN4")
    coefficients = np.array([-0.9, -1.1, -1.3, -1.7])
    assert np.allclose(
        basis @ coefficients,
        [-1.3, -1.1, -0.9, -0.9, -0.9, -0.9, -0.9],
    )
    assert np.allclose(basis[:, 3], 0.0)


def test_compute_is_global_no_go_and_withholds_matched_values():
    result = m.compute(n=1000, seed=8)
    assert result["verdict"]["decision"] == "NO-GO"
    assert not result["verdict"]["exact_matched_prior_identifiable_by_importance_reweighting"]
    assert all(row["no_go"] for row in result["grammars"].values())
    assert all(row["matched_fate"] is None for row in result["grammars"].values())
    assert all(row["diagnostics"]["ess"] is None for row in result["grammars"].values())
    assert all(row["diagnostics"]["support_overlap_fraction"] is None for row in result["grammars"].values())


def test_compute_deterministic_and_json_stable():
    a = m.compute(n=1000, seed=7)
    b = m.compute(n=1000, seed=7)
    assert a == b
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_native_context_probabilities_are_simplexes():
    result = m.compute(n=1200, seed=9)
    for row in result["grammars"].values():
        probs = row["native_fate_context_only"]
        assert np.isclose(sum(probs.values()), 1.0)
        assert all(0.0 <= p <= 1.0 for p in probs.values())


def test_invalid_sample_count_rejected():
    for n in (0, -1):
        try:
            m.compute(n=n)
        except ValueError:
            pass
        else:
            raise AssertionError("non-positive n must be rejected")
