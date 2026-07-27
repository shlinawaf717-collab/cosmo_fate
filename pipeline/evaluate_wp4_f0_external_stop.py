#!/usr/bin/env python3
"""Evaluate the frozen WP4 F0 external convergence policy.

This program is authoritative only when an activation manifest with matching
hashes exists.  It never signals sampler processes.  It maintains the
two-pass state and writes a stop-eligibility artifact for the separate
transactional finalizer.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from pipeline.monitor_wp4_f0 import collect_diagnostics


ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "plan/wp4_f0_external_convergence_policy.json"
DEFAULT_ACTIVATION = (
    ROOT
    / "runs/prd_extension/wp4_full_cmb/f0/external_stop_activation.json"
)
DEFAULT_STATE_DIR = (
    ROOT / "runs/prd_extension/wp4_full_cmb/f0/external_monitor"
)
SCHEMA_VERSION = "wp4-f0-authoritative-external-evaluation-v1"


class ExternalEvaluationError(RuntimeError):
    """Raised when the frozen external policy cannot be evaluated safely."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
        temporary = Path(handle.name)
    os.replace(temporary, path)


def _append_jsonl(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    try:
        os.write(descriptor, line.encode("utf-8"))
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def validate_activation(activation_path: Path, policy: dict) -> dict:
    if not activation_path.is_file():
        raise ExternalEvaluationError(
            f"activation manifest missing: {activation_path}"
        )
    activation = _load_json(activation_path)
    if activation.get("status") != "ACTIVE":
        raise ExternalEvaluationError("external stop is not ACTIVE")
    checks = {
        "policy": POLICY_PATH,
        "statistics": ROOT / policy["implementation"]["statistics_path"],
        "evaluator": Path(__file__).resolve(),
    }
    for name, path in checks.items():
        registered = activation["hashes"][name]
        if Path(registered["path"]).resolve() != path.resolve():
            raise ExternalEvaluationError(f"{name} path mismatch")
        actual = sha256_file(path)
        if actual != registered["sha256"]:
            raise ExternalEvaluationError(f"{name} hash mismatch")
    if (
        activation["hashes"]["statistics"]["sha256"]
        != policy["implementation"]["statistics_sha256"]
    ):
        raise ExternalEvaluationError("policy/activation statistics hash mismatch")
    return activation


def policy_gates(diagnostics: dict, policy: dict) -> dict[str, bool]:
    r_policy = policy["statistics"]["rminus1"]
    r_values = diagnostics["rminus1"]["by_burn_fraction"]
    primary_key = f"{r_policy['primary_row_burn_fraction']:.1f}"
    primary = (
        r_values[primary_key] < r_policy["primary_exclusive_maximum"]
    )
    sensitivity = all(
        r_values[f"{fraction:.1f}"]
        < r_policy["sensitivity_exclusive_maximum"]
        for fraction in r_policy["sensitivity_row_burn_fractions"]
    )
    ess_policy = policy["statistics"]["ess"]
    bulk = diagnostics["ess"]["bulk_by_parameter"]
    tail = diagnostics["ess"]["tail_by_parameter"]
    gated = ess_policy["gated_parameters"]
    return {
        "rminus1_primary": primary,
        "rminus1_burn_sensitivity": sensitivity,
        "bulk_ess_w_wa": all(
            bulk[name] > ess_policy["bulk_exclusive_minimum"]
            for name in gated
        ),
        "tail_ess_w_wa": all(
            tail[name] > ess_policy["tail_exclusive_minimum"]
            for name in gated
        ),
    }


def _snapshot_identity(payload: dict) -> str:
    canonical = json.dumps(
        {
            "chain_snapshots": payload["chain_snapshots"],
            "rminus1": payload["rminus1"],
            "ess": payload["ess"],
            "policy_gates": payload["policy_gates"],
            "policy_sha256": payload["policy_sha256"],
            "statistics_sha256": payload["statistics_sha256"],
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _pass_reference(payload: dict, snapshot_path: Path) -> dict:
    return {
        "snapshot_path": str(snapshot_path),
        "snapshot_sha256": payload["snapshot_sha256"],
        "captured_at_end_utc": payload["captured_at_end_utc"],
        "rows": [item["rows"] for item in payload["chain_snapshots"]],
        "chain_sha256": [
            item["sha256"] for item in payload["chain_snapshots"]
        ],
        "policy_sha256": payload["policy_sha256"],
        "statistics_sha256": payload["statistics_sha256"],
    }


def apply_repeated_pass_state(
    payload: dict,
    prior_state: dict | None,
    policy: dict,
    snapshot_path: Path,
) -> tuple[dict, dict | None]:
    all_pass = all(payload["policy_gates"].values())
    minimum_rows = policy["repeated_pass"]["minimum_new_complete_rows_per_chain"]
    state = dict(prior_state or {})
    if not all_pass:
        payload["status"] = "AUTHORITATIVE_CONTINUE"
        payload["consecutive_passes"] = 0
        payload["stop_eligible"] = False
        state = {
            "schema_version": "wp4-f0-external-pass-state-v1",
            "updated_at_utc": _utc_now(),
            "first_pass": None,
            "last_evaluation_status": payload["status"],
        }
        return state, None

    current = _pass_reference(payload, snapshot_path)
    first = state.get("first_pass")
    if not first:
        payload["status"] = "AUTHORITATIVE_PASS_1"
        payload["consecutive_passes"] = 1
        payload["stop_eligible"] = False
        state = {
            "schema_version": "wp4-f0-external-pass-state-v1",
            "updated_at_utc": _utc_now(),
            "first_pass": current,
            "last_evaluation_status": payload["status"],
        }
        return state, None

    hashes_match = (
        first["policy_sha256"] == payload["policy_sha256"]
        and first["statistics_sha256"] == payload["statistics_sha256"]
    )
    row_growth = [
        current_row - first_row
        for current_row, first_row in zip(current["rows"], first["rows"])
    ]
    chain_hashes_changed = all(
        current_hash != first_hash
        for current_hash, first_hash in zip(
            current["chain_sha256"], first["chain_sha256"]
        )
    )
    separated = (
        hashes_match
        and min(row_growth) >= minimum_rows
        and chain_hashes_changed
    )
    payload["row_growth_since_first_pass"] = row_growth
    if not separated:
        payload["status"] = "AUTHORITATIVE_PASS_WAITING_FOR_SEPARATION"
        payload["consecutive_passes"] = 1
        payload["stop_eligible"] = False
        state["updated_at_utc"] = _utc_now()
        state["last_evaluation_status"] = payload["status"]
        return state, None

    payload["status"] = "STOP_ELIGIBLE"
    payload["consecutive_passes"] = 2
    payload["stop_eligible"] = True
    eligibility = {
        "schema_version": "wp4-f0-stop-eligibility-v1",
        "created_at_utc": _utc_now(),
        "policy_sha256": payload["policy_sha256"],
        "statistics_sha256": payload["statistics_sha256"],
        "first_pass": first,
        "second_pass": current,
        "minimum_row_growth": min(row_growth),
    }
    state["updated_at_utc"] = _utc_now()
    state["last_evaluation_status"] = payload["status"]
    state["second_pass"] = current
    return state, eligibility


def evaluate_once(
    activation_path: Path = DEFAULT_ACTIVATION,
    state_dir: Path = DEFAULT_STATE_DIR,
) -> dict:
    policy = _load_json(POLICY_PATH)
    activation = validate_activation(activation_path, policy)
    chain_paths = [ROOT / path for path in policy["chains"]]
    burns = [
        r
        for r in (
            policy["statistics"]["rminus1"]["primary_row_burn_fraction"],
            *policy["statistics"]["rminus1"][
                "sensitivity_row_burn_fractions"
            ],
        )
    ]
    diagnostics = collect_diagnostics(
        chain_paths,
        burn_fractions=burns,
        primary_burn=policy["statistics"]["ess"]["row_burn_fraction"],
    )
    payload = {
        **diagnostics,
        "schema_version": SCHEMA_VERSION,
        "decision_authority": True,
        "sampler_signal_capability": False,
        "activation_path": str(activation_path),
        "activation_sha256": sha256_file(activation_path),
        "policy_sha256": sha256_file(POLICY_PATH),
        "statistics_sha256": activation["hashes"]["statistics"]["sha256"],
    }
    payload.pop("candidate_gates", None)
    payload["policy_gates"] = policy_gates(payload, policy)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    snapshot_path = state_dir / "snapshots" / f"{timestamp}.json"
    # The identity excludes repeated-pass metadata and is fixed before writing.
    payload["snapshot_sha256"] = _snapshot_identity(payload)
    prior_state_path = state_dir / "pass_state.json"
    prior_state = (
        _load_json(prior_state_path) if prior_state_path.is_file() else None
    )
    state, eligibility = apply_repeated_pass_state(
        payload, prior_state, policy, snapshot_path
    )
    _atomic_json(snapshot_path, payload)
    _atomic_json(state_dir / "latest.json", payload)
    _atomic_json(prior_state_path, state)
    _append_jsonl(state_dir / "history.jsonl", payload)
    if eligibility is not None:
        _atomic_json(state_dir / "stop_eligible.json", eligibility)
    else:
        eligible_path = state_dir / "stop_eligible.json"
        if eligible_path.exists():
            eligible_path.unlink()
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--activation", type=Path, default=DEFAULT_ACTIVATION)
    parser.add_argument("--state-dir", type=Path, default=DEFAULT_STATE_DIR)
    args = parser.parse_args()
    payload = evaluate_once(args.activation, args.state_dir)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "stop_eligible": payload["stop_eligible"],
                "rows": [
                    item["rows"] for item in payload["chain_snapshots"]
                ],
                "policy_gates": payload["policy_gates"],
                "snapshot_sha256": payload["snapshot_sha256"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
