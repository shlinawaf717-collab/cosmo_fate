import hashlib
import json
from pathlib import Path

from pipeline.monitor_wp4_f0 import SAMPLED_PARAMETERS


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "plan/wp4_f0_external_convergence_policy.json"
PROSE = ROOT / "plan/WP4_F0_EXTERNAL_CONVERGENCE_POLICY.md"
AMENDMENTS = ROOT / "plan/PRD_EXTENSION_AMENDMENTS.md"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_policy_is_frozen_and_matches_statistics_implementation():
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    assert policy["status"] == "FROZEN_DURING_F0_BEFORE_SCIENTIFIC_ENDPOINTS"
    implementation = ROOT / policy["implementation"]["statistics_path"]
    assert _sha256(implementation) == policy["implementation"]["statistics_sha256"]
    assert policy["sampled_parameters"] == list(SAMPLED_PARAMETERS)


def test_policy_gates_and_repeated_pass_are_explicit():
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    rminus1 = policy["statistics"]["rminus1"]
    assert rminus1["primary_row_burn_fraction"] == 0.5
    assert rminus1["primary_exclusive_maximum"] == 0.01
    assert rminus1["sensitivity_row_burn_fractions"] == [0.2, 0.7]
    assert rminus1["sensitivity_exclusive_maximum"] == 0.02
    ess = policy["statistics"]["ess"]
    assert ess["gated_parameters"] == ["w", "wa"]
    assert ess["bulk_exclusive_minimum"] == 1000
    assert ess["tail_exclusive_minimum"] == 400
    repeated = policy["repeated_pass"]
    assert repeated["required_consecutive_authoritative_passes"] == 2
    assert repeated["minimum_new_complete_rows_per_chain"] == 320


def test_policy_preserves_blinding_and_reversible_stop():
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    prohibited = set(policy["blinding"]["prohibited"])
    assert "posterior_locations" in prohibited
    assert "likelihood_values" in prohibited
    assert "fate_quantities" in prohibited
    stop = policy["stop_transaction"]
    assert stop["recompute_all_gates_after_pause"] is True
    assert stop["resume_all_children_on_failure"] is True
    assert stop["edit_cobaya_checkpoint"] is False


def test_prose_and_amendment_link_machine_policy():
    prose = PROSE.read_text(encoding="utf-8")
    amendments = AMENDMENTS.read_text(encoding="utf-8")
    assert "wp4_f0_external_convergence_policy.json" in prose
    assert "## PRD-A006" in amendments
    assert "WP4_F0_EXTERNAL_CONVERGENCE_POLICY.md" in amendments
