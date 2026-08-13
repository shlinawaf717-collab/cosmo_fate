#!/usr/bin/env python3
"""Freeze the prospective F1 stopping policy and activation hash closure."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from pipeline.run_wp4_f1 import (
    CONFIG, INPUT_MANIFEST, PROPOSAL, RUN_PLAN, RUN_ROOT, prepare,
)
from pipeline.wp4_preflight import ROOT, sha256_file


POLICY = ROOT / "plan/wp4_f1_external_convergence_policy.json"
ACTIVATION = RUN_ROOT / "external_stop_activation.json"
STATISTICS = ROOT / "pipeline/monitor_wp4_f1.py"
STATISTICS_BASE = ROOT / "pipeline/monitor_wp4_f0.py"
EVALUATOR = ROOT / "pipeline/evaluate_wp4_f1_external_stop.py"
FINALIZER = ROOT / "pipeline/finalize_wp4_f1_external_stop.py"
CONTROLLER = ROOT / "pipeline/run_wp4_f1_external_controller.py"


class F1FreezeError(RuntimeError):
    """Raised when prospective freezing is no longer safe."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _relative_record(path: Path) -> dict:
    return {"path": str(path.relative_to(ROOT)), "sha256": sha256_file(path)}


def _atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
        temporary = Path(handle.name)
    os.replace(temporary, path)


def build_policy() -> dict:
    return {
        "schema_version": "wp4-f1-external-convergence-policy-v1",
        "status": "PROSPECTIVELY_FROZEN_BEFORE_F1_PRODUCTION",
        "classification": "prospective_operational_definition",
        "decision_authority": True,
        "chains": [
            f"runs/prd_extension/wp4_full_cmb/f1/c{i}/chain.1.txt"
            for i in range(1, 5)
        ],
        "sampled_parameters": [
            "logA", "ns", "theta_MC_100", "ombh2", "omch2", "tau", "w", "wa", "Mb",
            "A_planck", "amp_143", "amp_217", "amp_143x217", "n_143", "n_217",
            "n_143x217", "calTE", "calEE",
        ],
        "statistics": {
            "rminus1": {
                "definition": "Cobaya_3.6.2_MPI_multivariate",
                "primary_row_burn_fraction": 0.5,
                "primary_exclusive_maximum": 0.01,
                "sensitivity_row_burn_fractions": [0.2, 0.7],
                "sensitivity_exclusive_maximum": 0.02,
                "parameters": "all_18_sampled",
            },
            "ess": {
                "row_burn_fraction": 0.5,
                "weight_handling": "expand_integer_weights_as_metropolis_dwell_states",
                "chain_equalization": "common_final_weighted_length",
                "split_chains": True,
                "bulk_definition": "pooled_rank_normalized_geyer_initial_positive_monotone",
                "tail_definition": "minimum_binary_indicator_ess_at_pooled_q05_q95",
                "gated_parameters": ["w", "wa"],
                "bulk_exclusive_minimum": 1000,
                "tail_exclusive_minimum": 400,
            },
        },
        "repeated_pass": {
            "required_consecutive_authoritative_passes": 2,
            "minimum_new_complete_rows_per_chain": 320,
            "require_changed_chain_hashes": True,
            "failed_intervening_snapshot_resets_sequence": True,
        },
        "snapshot": {
            "open_mode": "read_only",
            "capture_at_most_initial_file_size": True,
            "discard_partial_final_line": True,
            "hash_exact_captured_prefix": True,
            "final_stop_snapshot_requires_paused_children_and_stable_sizes": True,
        },
        "stop_transaction": {
            "pause_only_cobaya_children": True,
            "recompute_all_gates_after_pause": True,
            "resume_all_children_on_failure": True,
            "fsync_final_audit_before_termination": True,
            "edit_cobaya_checkpoint": False,
            "resume_command": "PYTHONPATH=. .venv/bin/python pipeline/run_wp4_f1.py --jobs 4",
        },
        "blinding": {
            "sampling_phase_allowed": [
                "complete_row_counts", "summed_integer_weights", "file_sizes_mtimes_sha256",
                "registered_convergence_statistics", "boolean_gate_states", "integrity_hashes",
            ],
            "sampling_phase_prohibited": [
                "posterior_locations", "posterior_intervals", "best_fit_points",
                "likelihood_values", "model_comparison_statistics", "fate_quantities",
            ],
        },
        "implementation": {
            "statistics_path": str(STATISTICS.relative_to(ROOT)),
            "statistics_sha256": sha256_file(STATISTICS),
            "statistics_base_path": str(STATISTICS_BASE.relative_to(ROOT)),
            "statistics_base_sha256": sha256_file(STATISTICS_BASE),
            "numpy": "2.5.0", "scipy": "1.16.2", "cobaya": "3.6.2",
        },
    }


def freeze() -> tuple[dict, dict]:
    sample_files = sorted(RUN_ROOT.glob("c*/chain.*.txt"))
    if sample_files:
        raise F1FreezeError("cannot prospectively refreeze after F1 sample files exist")
    plan = prepare()
    policy = build_policy()
    _atomic_json(POLICY, policy)
    hashes = {
        "policy": _relative_record(POLICY),
        "statistics": _relative_record(STATISTICS),
        "statistics_base": _relative_record(STATISTICS_BASE),
        "evaluator": _relative_record(EVALUATOR),
        "finalizer": _relative_record(FINALIZER),
        "controller": _relative_record(CONTROLLER),
    }
    runtime_hashes = {
        "run_plan": _relative_record(RUN_PLAN),
        "base_config": _relative_record(CONFIG),
        "proposal_covariance": _relative_record(PROPOSAL),
        "input_manifest": _relative_record(INPUT_MANIFEST),
    }
    for chain in plan["chains"]:
        path = ROOT / chain["run_yaml"]
        runtime_hashes[f"chain_{chain['chain']}_run_yaml"] = _relative_record(path)
    activation = {
        "schema_version": "wp4-f1-external-stop-activation-v1",
        "status": "ACTIVE_BEFORE_PRODUCTION",
        "activated_at_utc": _utc_now(),
        "first_authoritative_evaluation_must_follow_production_start": True,
        "pre_production_diagnostics_count_as_passes": False,
        "hashes": hashes,
        "runtime_hashes": runtime_hashes,
        "blinding_confirmation": {
            "f1_samples_exist_at_activation": False,
            "f1_posterior_locations_or_intervals_inspected": False,
            "f1_best_fit_or_likelihood_values_inspected": False,
            "f1_fate_quantities_inspected": False,
            "f1_scientific_endpoints_inspected": False,
        },
    }
    _atomic_json(ACTIVATION, activation)
    return policy, activation


if __name__ == "__main__":
    policy, activation = freeze()
    print(json.dumps({"policy": policy["status"], "activation": activation["status"]}, sort_keys=True))
