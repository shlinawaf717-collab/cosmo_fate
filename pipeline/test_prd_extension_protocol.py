import hashlib
import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "plan/prd_extension_protocol.json"


def load_spec():
    return json.loads(SPEC.read_text(encoding="utf-8"))


def test_baseline_identity_and_pdf_hash():
    spec = load_spec()
    baseline = spec["baseline"]
    assert spec["schema_version"] == "prd-extension-protocol-v1"
    assert len(baseline["commit"]) == 40
    assert baseline["tag"] == "paper-v1x-final-20260722"
    pdf = ROOT / baseline["pdf"]
    assert pdf.exists()
    assert hashlib.sha256(pdf.read_bytes()).hexdigest() == baseline["pdf_sha256"]


def test_extension_cannot_overwrite_v1x_roots():
    spec = load_spec()
    sep = spec["separation"]
    assert sep["v1x_artifacts_read_only"] is True
    root = sep["extension_results_root"]
    assert root.startswith("runs/prd_extension")
    assert root not in sep["forbidden_overwrite_roots"]
    assert {"runs/gate2", "runs/phase2", "runs/phase3"} <= set(
        sep["forbidden_overwrite_roots"]
    )


def test_null500_arithmetic_and_no_optional_stopping():
    null = load_spec()["wp2_null500"]
    assert null["existing_noisy"] + null["append_noisy"] == null["noisy_total"] == 500
    assert null["existing_indices"] == [1, 100]
    assert null["append_indices"] == [101, 500]
    assert null["zero_noise_in_null_distribution"] is False
    assert null["finite_p_rule"] == "(K+1)/(N+1)"
    assert null["optional_stopping"] is False


def test_power_grid_is_symmetric_and_seeded():
    power = load_spec()["wp3_power"]
    values = np.asarray(power["truth_values"], dtype=float)
    assert 0.0 not in values
    assert np.allclose(values, -values[::-1])
    assert len(values) == len(power["truth_ids"]) == len(power["generator_seeds"]) == 6
    assert len(set(power["generator_seeds"])) == 6
    assert power["noisy_mocks_per_truth"] == 100
    assert power["optional_stopping"] is False


def test_full_cmb_and_growth_gates_are_not_short_circuited():
    spec = load_spec()
    cmb = spec["wp4_full_cmb_cpl"]
    assert cmb["reproduction_run_id"] == "F0"
    assert cmb["primary_science_run_id"] == "F1"
    assert "Pantheon+ without SH0ES" in cmb["reproduction_data"]
    assert "Pantheon+SH0ES" in cmb["primary_science_data"]
    assert spec["wp5_bin4"]["requires_wp4_go"] is True
    assert spec["wp5_bin4"]["failed_gate_action"].startswith("NO-GO")
    growth = spec["wp6_growth"]
    assert growth["forbid_marginal_point_compilation"] is True
    assert growth["forbid_overlap_without_joint_covariance"] is True
    assert growth["decision_must_precede_fate_calculation"] is True


def test_fs7_prior_covariances_are_positive_definite():
    fs = load_spec()["wp7_fs7"]
    assert fs["function_bound_grid_size"] == 512
    assert fs["function_bound_grid_a"] == [0.25, 4.0]
    x = np.log(np.asarray(fs["free_a_nodes"], dtype=float))
    settings = [fs["primary_hyperparameters"], *fs["sensitivity_hyperparameters"]]
    for setting in settings:
        sigma = float(setting["sigma_f"])
        ell = float(setting["ell"])
        dx = x[:, None] - x[None, :]
        cov = sigma**2 * np.exp(-0.5 * dx**2 / ell**2)
        cov += float(fs["jitter"]) * np.eye(len(x))
        np.linalg.cholesky(cov)
    assert fs["importance_reweight_native_grammars"] is False
    assert fs["future_extension"] == "constant at final node for a>=4"
