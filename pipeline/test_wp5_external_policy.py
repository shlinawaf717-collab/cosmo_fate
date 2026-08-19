import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_wp5_policy_freezes_three_independent_widths_and_20d_gate():
    policy = json.loads((ROOT / "plan/wp5_external_convergence_policy.json").read_text())
    assert policy["status"] == "FROZEN_BEFORE_WP5_PRODUCTION"
    assert len(policy["sampled_parameters"]) == 20
    assert set(policy["execution"]["widths"]) == {"0p005", "0p01", "0p02"}
    assert policy["execution"]["max_parallel_chains"] == 8
    assert policy["statistics"]["ess"]["gated_parameters"] == ["w1", "w2", "w3", "w4"]
    assert policy["repeated_pass"]["minimum_new_complete_rows_per_chain"] == 320
