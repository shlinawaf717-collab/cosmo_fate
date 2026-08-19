#!/usr/bin/env python3
"""Evaluate the frozen WSL2 F1 policy and maintain two-pass state."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from tools.monitor_wsl2_f1 import ROOT, collect


POLICY = ROOT / "work/f1/external_convergence_policy.json"
ACTIVATION = ROOT / "work/f1/external_stop_activation.json"
STATE = ROOT / "work/f1/external_monitor"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush(); os.fsync(handle.fileno()); temporary = Path(handle.name)
    os.replace(temporary, path)


def append(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    try:
        os.write(fd, (json.dumps(payload, sort_keys=True) + "\n").encode()); os.fsync(fd)
    finally:
        os.close(fd)


def validate() -> tuple[dict, dict]:
    policy, activation = load(POLICY), load(ACTIVATION)
    if activation["status"] != "ACTIVE_BEFORE_WSL2_PRODUCTION":
        raise RuntimeError("WSL2 activation is not authoritative")
    for group in ("hashes", "runtime_hashes", "preflight_hashes"):
        for name, record in activation[group].items():
            path = ROOT / record["path"]
            if sha(path) != record["sha256"]:
                raise RuntimeError(f"activation hash mismatch: {group}.{name}")
    return policy, activation


def gates(diag: dict, policy: dict) -> dict:
    r = policy["statistics"]["rminus1"]
    values = diag["rminus1"]["by_burn_fraction"]
    ess = policy["statistics"]["ess"]
    bulk, tail = diag["ess"]["bulk_by_parameter"], diag["ess"]["tail_by_parameter"]
    return {
        "rminus1_primary": values["0.5"] < r["primary_exclusive_maximum"],
        "rminus1_burn_sensitivity": values["0.2"] < r["sensitivity_exclusive_maximum"] and values["0.7"] < r["sensitivity_exclusive_maximum"],
        "bulk_ess_w_wa": all(bulk[name] > ess["bulk_exclusive_minimum"] for name in ("w", "wa")),
        "tail_ess_w_wa": all(tail[name] > ess["tail_exclusive_minimum"] for name in ("w", "wa")),
    }


def evaluate() -> dict:
    policy, activation = validate()
    diag = collect([ROOT / path for path in policy["chains"]])
    payload = {**diag, "schema_version": "wp4-f1-wsl2-authoritative-evaluation-v1", "decision_authority": True, "policy_sha256": sha(POLICY), "statistics_sha256": activation["hashes"]["statistics"]["sha256"]}
    payload.pop("candidate_gates", None)
    payload["policy_gates"] = gates(payload, policy)
    payload["snapshot_sha256"] = hashlib.sha256(json.dumps({key: payload[key] for key in ("chain_snapshots", "rminus1", "ess", "policy_gates", "policy_sha256", "statistics_sha256")}, sort_keys=True).encode()).hexdigest()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    snapshot = STATE / "snapshots" / f"{stamp}.json"
    state_path = STATE / "pass_state.json"
    prior = load(state_path) if state_path.exists() else {}
    rows = [item["rows"] for item in payload["chain_snapshots"]]
    hashes = [item["sha256"] for item in payload["chain_snapshots"]]
    current = {"snapshot_path": str(snapshot.relative_to(ROOT)), "snapshot_sha256": payload["snapshot_sha256"], "rows": rows, "chain_sha256": hashes, "policy_sha256": payload["policy_sha256"], "statistics_sha256": payload["statistics_sha256"]}
    eligible = None
    if not all(payload["policy_gates"].values()):
        payload.update(status="AUTHORITATIVE_CONTINUE", consecutive_passes=0, stop_eligible=False)
        state = {"first_pass": None, "last_evaluation_status": payload["status"]}
    elif not prior.get("first_pass"):
        payload.update(status="AUTHORITATIVE_PASS_1", consecutive_passes=1, stop_eligible=False)
        state = {"first_pass": current, "last_evaluation_status": payload["status"]}
    else:
        first = prior["first_pass"]
        growth = [a-b for a,b in zip(rows, first["rows"])]
        separated = min(growth) >= 320 and all(a != b for a,b in zip(hashes, first["chain_sha256"])) and first["policy_sha256"] == current["policy_sha256"] and first["statistics_sha256"] == current["statistics_sha256"]
        if separated:
            payload.update(status="STOP_ELIGIBLE", consecutive_passes=2, stop_eligible=True, row_growth_since_first_pass=growth)
            eligible = {"schema_version": "wp4-f1-wsl2-stop-eligibility-v1", "policy_sha256": payload["policy_sha256"], "statistics_sha256": payload["statistics_sha256"], "first_pass": first, "second_pass": current, "minimum_row_growth": min(growth)}
            state = {**prior, "second_pass": current, "last_evaluation_status": payload["status"]}
        else:
            payload.update(status="AUTHORITATIVE_PASS_WAITING_FOR_SEPARATION", consecutive_passes=1, stop_eligible=False, row_growth_since_first_pass=growth)
            state = {**prior, "last_evaluation_status": payload["status"]}
    atomic(snapshot, payload); atomic(STATE / "latest.json", payload); atomic(state_path, state); append(STATE / "history.jsonl", payload)
    eligible_path = STATE / "stop_eligible.json"
    if eligible: atomic(eligible_path, eligible)
    elif eligible_path.exists(): eligible_path.unlink()
    return payload


if __name__ == "__main__":
    payload = evaluate()
    print(json.dumps({"status": payload["status"], "rows": [x["rows"] for x in payload["chain_snapshots"]], "policy_gates": payload["policy_gates"]}, sort_keys=True))
