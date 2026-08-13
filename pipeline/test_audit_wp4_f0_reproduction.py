from pathlib import Path

import numpy as np

from pipeline.audit_wp4_f0_reproduction import (
    compare_moments,
    delta_chi2_audit,
    weighted_moments,
)


def _write_table(path: Path, header: list[str], rows: list[list[float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savetxt(path, np.asarray(rows), header=" ".join(header))


def test_weighted_moments_applies_row_burn_and_integer_weights(tmp_path):
    path = tmp_path / "chain.1.txt"
    _write_table(
        path,
        ["weight", "w", "wa", "omegam", "H0"],
        [
            [9, -9, -9, -9, -9],
            [1, -1, 0, 0.3, 60],
            [3, -3, 2, 0.4, 80],
        ],
    )
    result, records = weighted_moments([path], burn_fraction=1 / 3)
    assert result["w0"]["mean"] == -2.5
    assert result["H0"]["mean"] == 75.0
    assert records[0]["full_rows"] == 3
    assert records[0]["post_burn_weight"] == 4


def test_compare_moments_reports_independent_mean_and_sd_gates():
    local = {name: {"mean": 0.1, "sd": 1.05} for name in ("w0", "wa", "Omega_m", "H0")}
    official = {name: {"mean": 0.0, "sd": 1.0} for name in local}
    result = compare_moments(
        local,
        official,
        {"max_mean_shift_pooled_sigma": 0.2, "max_sd_fractional_difference": 0.1},
    )
    assert result["all_mean_gates_pass"] is True
    assert result["all_sd_gates_pass"] is True


def test_delta_chi2_gate_and_pending_state(tmp_path):
    header = [
        "weight",
        "minuslogpost",
        "minuslogprior",
        "chi2",
        "chi2__BAO",
        "chi2__like_a",
        "chi2__like_b",
    ]
    official = {"cpl": tmp_path / "oc.txt", "lcdm": tmp_path / "ol.txt"}
    local = {"cpl": tmp_path / "lc.txt", "lcdm": tmp_path / "ll.txt"}
    _write_table(official["cpl"], header, [[1, 5, 1, 8, 8, 3, 5]])
    _write_table(official["lcdm"], header, [[1, 7, 1, 12, 12, 5, 7]])
    pending = delta_chi2_audit(official, local, 1.0)
    assert pending["status"] == "PENDING_LOCAL_OPTIMIZATION"
    _write_table(local["cpl"], header, [[1, 5, 1, 8.2, 8.2, 3.1, 5.1]])
    _write_table(local["lcdm"], header, [[1, 7, 1, 12.1, 12.1, 5.05, 7.05]])
    result = delta_chi2_audit(official, local, 1.0)
    assert result["status"] == "PASS"
    assert np.isclose(result["absolute_delta_chi2_difference"], 0.1)
