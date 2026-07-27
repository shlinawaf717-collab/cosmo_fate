from copy import deepcopy
from pathlib import Path

from pipeline.evaluate_wp4_f0_external_stop import (
    apply_repeated_pass_state,
    policy_gates,
)


def _policy():
    return {
        "statistics": {
            "rminus1": {
                "primary_row_burn_fraction": 0.5,
                "primary_exclusive_maximum": 0.01,
                "sensitivity_row_burn_fractions": [0.2, 0.7],
                "sensitivity_exclusive_maximum": 0.02,
            },
            "ess": {
                "gated_parameters": ["w", "wa"],
                "bulk_exclusive_minimum": 1000,
                "tail_exclusive_minimum": 400,
            },
        },
        "repeated_pass": {"minimum_new_complete_rows_per_chain": 320},
    }


def _payload(rows=(1000, 1000, 1000, 1000), suffix="a"):
    return {
        "captured_at_end_utc": "2026-07-27T00:00:00+00:00",
        "chain_snapshots": [
            {"rows": row, "sha256": f"{index}-{suffix}"}
            for index, row in enumerate(rows)
        ],
        "policy_sha256": "policy",
        "statistics_sha256": "stats",
        "snapshot_sha256": f"snapshot-{suffix}",
        "policy_gates": {
            "rminus1_primary": True,
            "rminus1_burn_sensitivity": True,
            "bulk_ess_w_wa": True,
            "tail_ess_w_wa": True,
        },
    }


def test_policy_gates_apply_registered_parameters_only():
    diagnostics = {
        "rminus1": {
            "by_burn_fraction": {"0.5": 0.009, "0.2": 0.019, "0.7": 0.019}
        },
        "ess": {
            "bulk_by_parameter": {"w": 1001, "wa": 1002, "other": 1},
            "tail_by_parameter": {"w": 401, "wa": 402, "other": 1},
        },
    }
    assert all(policy_gates(diagnostics, _policy()).values())


def test_failed_snapshot_resets_first_pass():
    payload = _payload()
    payload["policy_gates"]["rminus1_primary"] = False
    state, eligibility = apply_repeated_pass_state(
        payload, {"first_pass": {"irrelevant": True}}, _policy(), Path("fail.json")
    )
    assert state["first_pass"] is None
    assert eligibility is None
    assert payload["consecutive_passes"] == 0


def test_two_passes_require_row_growth_and_new_hashes():
    first_payload = _payload()
    state, eligibility = apply_repeated_pass_state(
        first_payload, None, _policy(), Path("first.json")
    )
    assert eligibility is None
    close_payload = _payload((1200, 1400, 1400, 1400), suffix="b")
    state, eligibility = apply_repeated_pass_state(
        close_payload, state, _policy(), Path("close.json")
    )
    assert eligibility is None
    assert close_payload["status"].endswith("WAITING_FOR_SEPARATION")
    second_payload = _payload((1320, 1320, 1320, 1320), suffix="c")
    state, eligibility = apply_repeated_pass_state(
        second_payload, state, _policy(), Path("second.json")
    )
    assert eligibility is not None
    assert second_payload["status"] == "STOP_ELIGIBLE"
    assert eligibility["minimum_row_growth"] == 320


def test_changed_policy_hash_cannot_form_second_pass():
    first_payload = _payload()
    state, _ = apply_repeated_pass_state(
        first_payload, None, _policy(), Path("first.json")
    )
    second_payload = deepcopy(_payload((1400, 1400, 1400, 1400), suffix="b"))
    second_payload["policy_sha256"] = "different"
    state, eligibility = apply_repeated_pass_state(
        second_payload, state, _policy(), Path("second.json")
    )
    assert eligibility is None
    assert second_payload["stop_eligible"] is False
