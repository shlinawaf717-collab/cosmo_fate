#!/usr/bin/env python3
"""Evaluate one WP5 width under the prospectively frozen external policy."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from pipeline.monitor_wp5_bin4 import ROOT, WIDTH_TAGS, chain_paths, collect


SYSTEM_ROOT = ROOT / "runs/prd_extension/wp5_bin4/production_system"
POLICY = ROOT / "plan/wp5_external_convergence_policy.json"
ACTIVATION = SYSTEM_ROOT / "activation.json"


class WP5ExternalError(RuntimeError):
    pass


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(payload, handle, indent=2, sort_keys=True); handle.write("\n")
        handle.flush(); os.fsync(handle.fileno()); temporary = Path(handle.name)
    os.replace(temporary, path)


def append(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    try: os.write(descriptor, (json.dumps(payload, sort_keys=True) + "\n").encode()); os.fsync(descriptor)
    finally: os.close(descriptor)


def validate() -> tuple[dict, dict]:
    policy = load(POLICY); activation = load(ACTIVATION)
    if policy.get("status") != "FROZEN_BEFORE_WP5_PRODUCTION":
        raise WP5ExternalError("WP5 policy is not frozen")
    if activation.get("status") != "ACTIVE_BEFORE_WP5_PRODUCTION":
        raise WP5ExternalError("WP5 activation is not authoritative")
    if sha(POLICY) != activation["policy_sha256"]:
        raise WP5ExternalError("WP5 policy hash mismatch")
    for name, record in activation["runtime_hashes"].items():
        path = ROOT / record["path"]
        if sha(path) != record["sha256"]:
            raise WP5ExternalError(f"WP5 runtime hash mismatch: {name}")
    for name, record in activation["input_hashes"].items():
        path = ROOT / record["path"]
        if sha(path) != record["sha256"]:
            raise WP5ExternalError(f"WP5 input hash mismatch: {name}")
    return policy, activation


def gates(diagnostics: dict, policy: dict) -> dict:
    r = policy["statistics"]["rminus1"]
    values = diagnostics["rminus1"]["by_burn_fraction"]
    ess = policy["statistics"]["ess"]
    parameters = ess["gated_parameters"]
    return {
        "rminus1_primary": values["0.5"] < r["primary_exclusive_maximum"],
        "rminus1_burn_sensitivity": values["0.2"] < r["sensitivity_exclusive_maximum"] and values["0.7"] < r["sensitivity_exclusive_maximum"],
        "bulk_ess_wbins": all(diagnostics["ess"]["bulk_by_parameter"][name] > ess["bulk_exclusive_minimum"] for name in parameters),
        "tail_ess_wbins": all(diagnostics["ess"]["tail_by_parameter"][name] > ess["tail_exclusive_minimum"] for name in parameters),
    }


def identity(payload: dict) -> str:
    keys = ("chain_snapshots", "rminus1", "ess", "policy_gates", "policy_sha256", "statistics_sha256")
    return hashlib.sha256(json.dumps({key: payload[key] for key in keys}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def evaluate(width_tag: str) -> dict:
    if width_tag not in WIDTH_TAGS: raise WP5ExternalError(width_tag)
    policy, activation = validate(); state_dir = SYSTEM_ROOT / f"delta_{width_tag}/external_monitor"
    diagnostics = collect(chain_paths(width_tag, SYSTEM_ROOT))
    payload = {**diagnostics, "schema_version": "wp5-bin4-authoritative-evaluation-v1",
               "decision_authority": True, "width_tag": width_tag,
               "policy_sha256": sha(POLICY),
               "statistics_sha256": activation["runtime_hashes"]["monitor"]["sha256"]}
    payload.pop("candidate_gates", None); payload["policy_gates"] = gates(payload, policy)
    payload["snapshot_sha256"] = identity(payload)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    snapshot = state_dir / "snapshots" / f"{stamp}.json"
    state_path = state_dir / "pass_state.json"
    prior = load(state_path) if state_path.exists() else {}
    rows = [item["rows"] for item in payload["chain_snapshots"]]
    hashes = [item["sha256"] for item in payload["chain_snapshots"]]
    current = {"snapshot_path": str(snapshot.relative_to(ROOT)), "snapshot_sha256": payload["snapshot_sha256"],
               "rows": rows, "chain_sha256": hashes, "policy_sha256": payload["policy_sha256"],
               "statistics_sha256": payload["statistics_sha256"]}
    eligibility = None
    if not all(payload["policy_gates"].values()):
        payload.update(status="AUTHORITATIVE_CONTINUE", consecutive_passes=0, stop_eligible=False)
        state = {"first_pass": None, "last_evaluation_status": payload["status"]}
    elif not prior.get("first_pass"):
        payload.update(status="AUTHORITATIVE_PASS_1", consecutive_passes=1, stop_eligible=False)
        state = {"first_pass": current, "last_evaluation_status": payload["status"]}
    else:
        first = prior["first_pass"]; growth = [a-b for a,b in zip(rows, first["rows"])]
        separated = min(growth) >= policy["repeated_pass"]["minimum_new_complete_rows_per_chain"] and all(a != b for a,b in zip(hashes, first["chain_sha256"])) and first["policy_sha256"] == current["policy_sha256"] and first["statistics_sha256"] == current["statistics_sha256"]
        if separated:
            payload.update(status="STOP_ELIGIBLE", consecutive_passes=2, stop_eligible=True, row_growth_since_first_pass=growth)
            eligibility = {"schema_version": "wp5-bin4-stop-eligibility-v1", "width_tag": width_tag,
                           "policy_sha256": payload["policy_sha256"], "statistics_sha256": payload["statistics_sha256"],
                           "first_pass": first, "second_pass": current, "minimum_row_growth": min(growth)}
            state = {**prior, "second_pass": current, "last_evaluation_status": payload["status"]}
        else:
            payload.update(status="AUTHORITATIVE_PASS_WAITING_FOR_SEPARATION", consecutive_passes=1, stop_eligible=False, row_growth_since_first_pass=growth)
            state = {**prior, "last_evaluation_status": payload["status"]}
    atomic(snapshot, payload); atomic(state_dir / "latest.json", payload); atomic(state_path, state)
    append(state_dir / "history.jsonl", payload)
    eligible_path = state_dir / "stop_eligible.json"
    if eligibility: atomic(eligible_path, eligibility)
    elif eligible_path.exists(): eligible_path.unlink()
    return payload


if __name__ == "__main__":
    import argparse
    parser=argparse.ArgumentParser(); parser.add_argument("width_tag", choices=WIDTH_TAGS); args=parser.parse_args()
    result=evaluate(args.width_tag); print(json.dumps({"status":result["status"],"width_tag":args.width_tag,"policy_gates":result["policy_gates"]}))
