import pytest

from pipeline.aggregate_nested_d0 import aggregate


def row(seed, rip, lnb):
    return {
        "seed": seed,
        "P_fate_weighted": {
            "CRUNCH": 0.0, "RIP": rip, "DS": 0.0,
            "DECAY": 1.0 - rip, "OTHER": 0.0,
        },
        "lnZ_CPL": -10.0 + lnb,
        "lnZ_LCDM": -10.0,
        "lnB_CPL_over_LCDM": lnb,
        "lnB_err": 0.2,
        "CPL_audit": {"ess": 100.0},
        "LCDM_audit": {"ess": 80.0},
    }


def test_aggregate_keeps_between_seed_and_internal_errors_separate():
    out = aggregate([row(1, 0.001, -1.5), row(2, 0.003, -2.0), row(3, 0.002, -1.0)])
    assert out["P_fate_weighted"]["RIP"] == pytest.approx(0.002)
    assert out["P_fate_between_seed_sd"]["RIP"] == pytest.approx(0.001)
    assert out["lnB_CPL_over_LCDM"] == pytest.approx(-1.5)
    assert out["lnB_between_seed_sd"] == pytest.approx(0.5)
    assert out["per_run_internal_lnB_errors"] == [0.2, 0.2, 0.2]


def test_aggregate_rejects_duplicate_or_single_seed():
    with pytest.raises(ValueError, match="at least two"):
        aggregate([row(1, 0.1, 0.0)])
    with pytest.raises(ValueError, match="unique"):
        aggregate([row(1, 0.1, 0.0), row(1, 0.2, 0.1)])
