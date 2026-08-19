import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_a013_changes_only_background_validation_target():
    payload = json.loads(
        (ROOT / "plan/wp5_smooth_background_amendment_a013.json").read_text()
    )
    assert payload["status"] == "approved_before_WP5_real_data_inference"
    assert payload["new_background_implementation_gate"]["H_relative_max"] == 1e-4
    assert payload["piecewise_role"] == "mandatory_separate_model_difference_diagnostic"
    unchanged = payload["unchanged"]
    assert unchanged["primary_delta_ln_a"] == 0.01
    assert unchanged["sensitivity_delta_ln_a"] == [0.005, 0.01, 0.02]
    assert unchanged["posterior_mean_max_pooled_sd"] == 0.1
    assert unchanged["P_RIP_max_absolute_difference"] == 0.02
    assert unchanged["optional_width_selection"] is False
