import hashlib
import json
from pathlib import Path

from pipeline.evaluate_wp4_f1_external_stop import policy_gates
from pipeline.freeze_wp4_f1_system import ACTIVATION, POLICY, ROOT
from pipeline.monitor_wp4_f1 import SAMPLED_PARAMETERS


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_f1_policy_is_prospective_and_explicit():
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    assert policy["status"] == "PROSPECTIVELY_FROZEN_BEFORE_F1_PRODUCTION"
    assert policy["sampled_parameters"] == list(SAMPLED_PARAMETERS)
    assert policy["statistics"]["rminus1"]["parameters"] == "all_18_sampled"
    assert policy["repeated_pass"]["minimum_new_complete_rows_per_chain"] == 320
    assert policy["stop_transaction"]["resume_all_children_on_failure"] is True


def test_f1_activation_closes_code_and_runtime_hashes():
    activation = json.loads(ACTIVATION.read_text(encoding="utf-8"))
    assert activation["status"] == "ACTIVE_BEFORE_PRODUCTION"
    assert activation["blinding_confirmation"]["f1_samples_exist_at_activation"] is False
    for group in ("hashes", "runtime_hashes"):
        for record in activation[group].values():
            path = ROOT / record["path"]
            assert path.is_file()
            assert _sha(path) == record["sha256"]


def test_f1_policy_gate_boundaries_are_strict():
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    diagnostics = {
        "rminus1": {"by_burn_fraction": {"0.5": 0.009, "0.2": 0.019, "0.7": 0.019}},
        "ess": {
            "bulk_by_parameter": {"w": 1001, "wa": 1001},
            "tail_by_parameter": {"w": 401, "wa": 401},
        },
    }
    assert all(policy_gates(diagnostics, policy).values())
    diagnostics["rminus1"]["by_burn_fraction"]["0.5"] = 0.01
    assert policy_gates(diagnostics, policy)["rminus1_primary"] is False
