#!/usr/bin/env python3
"""Evaluate the prospectively frozen WP4 F1 external stopping policy."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from pipeline.monitor_wp4_f1 import collect_diagnostics


ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "plan/wp4_f1_external_convergence_policy.json"
DEFAULT_ACTIVATION = ROOT / "runs/prd_extension/wp4_full_cmb/f1/external_stop_activation.json"
DEFAULT_STATE_DIR = ROOT / "runs/prd_extension/wp4_full_cmb/f1/external_monitor"


class ExternalEvaluationError(RuntimeError):
    """Raised when the frozen F1 policy cannot be evaluated safely."""


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
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
        temporary = Path(handle.name)
    os.replace(temporary, path)


def _append_jsonl(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    try:
        os.write(descriptor, (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode())
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def validate_activation(activation_path: Path, policy: dict) -> dict:
    if not activation_path.is_file():
        raise ExternalEvaluationError(f"activation manifest missing: {activation_path}")
    activation = _load_json(activation_path)
    if activation.get("status") != "ACTIVE_BEFORE_PRODUCTION":
        raise ExternalEvaluationError("F1 external stop is not active")
    checks = {
        "policy": POLICY_PATH,
        "statistics": ROOT / policy["implementation"]["statistics_path"],
        "statistics_base": ROOT / policy["implementation"]["statistics_base_path"],
        "evaluator": Path(__file__).resolve(),
    }
    for name, path in checks.items():
        registered = activation["hashes"][name]
        if (ROOT / registered["path"]).resolve() != path.resolve():
            raise ExternalEvaluationError(f"{name} path mismatch")
        if sha256_file(path) != registered["sha256"]:
            raise ExternalEvaluationError(f"{name} hash mismatch")
    return activation


def policy_gates(diagnostics: dict, policy: dict) -> dict[str, bool]:
    r = policy["statistics"]["rminus1"]
    values = diagnostics["rminus1"]["by_burn_fraction"]
    ess = policy["statistics"]["ess"]
    bulk = diagnostics["ess"]["bulk_by_parameter"]
    tail = diagnostics["ess"]["tail_by_parameter"]
    return {
        "rminus1_primary": values[f"{r['primary_row_burn_fraction']:.1f}"] < r["primary_exclusive_maximum"],
        "rminus1_burn_sensitivity": all(
            values[f"{fraction:.1f}"] < r["sensitivity_exclusive_maximum"]
            for fraction in r["sensitivity_row_burn_fractions"]
        ),
        "bulk_ess_w_wa": all(bulk[name] > ess["bulk_exclusive_minimum"] for name in ess["gated_parameters"]),
        "tail_ess_w_wa": all(tail[name] > ess["tail_exclusive_minimum"] for name in ess["gated_parameters"]),
    }


def _identity(payload: dict) -> str:
    keys = ("chain_snapshots", "rminus1", "ess", "policy_gates", "policy_sha256", "statistics_sha256")
    canonical = json.dumps({key: payload[key] for key in keys}, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(canonical).hexdigest()


def _pass_ref(payload: dict, path: Path) -> dict:
    return {
        "snapshot_path": str(path),
        "snapshot_sha256": payload["snapshot_sha256"],
        "rows": [item["rows"] for item in payload["chain_snapshots"]],
        "chain_sha256": [item["sha256"] for item in payload["chain_snapshots"]],
        "policy_sha256": payload["policy_sha256"],
        "statistics_sha256": payload["statistics_sha256"],
    }


def evaluate_once(activation_path: Path = DEFAULT_ACTIVATION, state_dir: Path = DEFAULT_STATE_DIR) -> dict:
    policy = _load_json(POLICY_PATH)
    activation = validate_activation(activation_path, policy)
    r = policy["statistics"]["rminus1"]
    burns = [r["primary_row_burn_fraction"], *r["sensitivity_row_burn_fractions"]]
    payload = collect_diagnostics(
        [ROOT / path for path in policy["chains"]], burns,
        policy["statistics"]["ess"]["row_burn_fraction"],
    )
    payload.update({
        "schema_version": "wp4-f1-authoritative-external-evaluation-v1",
        "decision_authority": True,
        "sampler_signal_capability": False,
        "activation_path": str(activation_path),
        "activation_sha256": sha256_file(activation_path),
        "policy_sha256": sha256_file(POLICY_PATH),
        "statistics_sha256": activation["hashes"]["statistics"]["sha256"],
    })
    payload.pop("candidate_gates", None)
    payload["policy_gates"] = policy_gates(payload, policy)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    snapshot_path = state_dir / "snapshots" / f"{stamp}.json"
    payload["snapshot_sha256"] = _identity(payload)
    state_path = state_dir / "pass_state.json"
    prior = _load_json(state_path) if state_path.is_file() else {}
    all_pass = all(payload["policy_gates"].values())
    first = prior.get("first_pass")
    eligibility = None
    if not all_pass:
        payload.update(status="AUTHORITATIVE_CONTINUE", consecutive_passes=0, stop_eligible=False)
        state = {"schema_version": "wp4-f1-external-pass-state-v1", "updated_at_utc": _utc_now(), "first_pass": None, "last_evaluation_status": payload["status"]}
    elif not first:
        payload.update(status="AUTHORITATIVE_PASS_1", consecutive_passes=1, stop_eligible=False)
        state = {"schema_version": "wp4-f1-external-pass-state-v1", "updated_at_utc": _utc_now(), "first_pass": _pass_ref(payload, snapshot_path), "last_evaluation_status": payload["status"]}
    else:
        current = _pass_ref(payload, snapshot_path)
        growth = [now - then for now, then in zip(current["rows"], first["rows"])]
        separated = (
            first["policy_sha256"] == current["policy_sha256"]
            and first["statistics_sha256"] == current["statistics_sha256"]
            and min(growth) >= policy["repeated_pass"]["minimum_new_complete_rows_per_chain"]
            and all(a != b for a, b in zip(first["chain_sha256"], current["chain_sha256"]))
        )
        payload["row_growth_since_first_pass"] = growth
        if separated:
            payload.update(status="STOP_ELIGIBLE", consecutive_passes=2, stop_eligible=True)
            eligibility = {"schema_version": "wp4-f1-stop-eligibility-v1", "created_at_utc": _utc_now(), "policy_sha256": payload["policy_sha256"], "statistics_sha256": payload["statistics_sha256"], "first_pass": first, "second_pass": current, "minimum_row_growth": min(growth)}
            state = {**prior, "updated_at_utc": _utc_now(), "second_pass": current, "last_evaluation_status": payload["status"]}
        else:
            payload.update(status="AUTHORITATIVE_PASS_WAITING_FOR_SEPARATION", consecutive_passes=1, stop_eligible=False)
            state = {**prior, "updated_at_utc": _utc_now(), "last_evaluation_status": payload["status"]}
    _atomic_json(snapshot_path, payload)
    _atomic_json(state_dir / "latest.json", payload)
    _atomic_json(state_path, state)
    _append_jsonl(state_dir / "history.jsonl", payload)
    eligible_path = state_dir / "stop_eligible.json"
    if eligibility:
        _atomic_json(eligible_path, eligibility)
    elif eligible_path.exists():
        eligible_path.unlink()
    return payload


if __name__ == "__main__":
    payload = evaluate_once()
    print(json.dumps({"status": payload["status"], "rows": [x["rows"] for x in payload["chain_snapshots"]], "policy_gates": payload["policy_gates"]}, sort_keys=True))
