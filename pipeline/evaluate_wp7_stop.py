#!/usr/bin/env python3
"""Authoritative repeated-pass evaluation for one WP7 setting."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from pipeline.audit_wp4_f0_reproduction import atomic_write_json
from pipeline.monitor_wp7 import ROOT, SETTINGS, SYSTEM, chain_paths, collect


POLICY = ROOT / "plan/wp7_execution_protocol.json"
ACTIVATION = SYSTEM / "activation.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def validate() -> tuple[dict, dict]:
    policy, activation = load(POLICY), load(ACTIVATION)
    if policy["status"] != "FROZEN_BEFORE_WP7_POSTERIOR_SAMPLING":
        raise RuntimeError("WP7 policy is not frozen")
    if activation["status"] != "READY_TO_START_WP7_REAL_DATA":
        raise RuntimeError("WP7 activation is not ready")
    if activation["policy"]["sha256"] != sha(POLICY):
        raise RuntimeError("WP7 policy hash mismatch")
    for record in activation["code"].values():
        if sha(ROOT / record["path"]) != record["sha256"]:
            raise RuntimeError(f"WP7 runtime hash mismatch: {record['path']}")
    return policy, activation


def policy_gates(diagnostics: dict, policy: dict) -> dict:
    return dict(diagnostics["candidate_gates"])


def evaluate(setting: str) -> dict:
    if setting not in SETTINGS:
        raise ValueError(setting)
    policy, activation = validate()
    state_dir = SYSTEM / setting / "external_monitor"
    diagnostics = collect(setting, chain_paths(setting))
    payload = {
        **diagnostics,
        "schema_version": "wp7-fs7-authoritative-evaluation-v1",
        "decision_authority": True,
        "policy_sha256": sha(POLICY),
        "monitor_sha256": activation["code"]["pipeline/monitor_wp7.py"]["sha256"],
    }
    payload["policy_gates"] = policy_gates(payload, policy)
    identity_source = {key: payload[key] for key in ("chain_snapshots", "rhat", "ess", "policy_gates", "policy_sha256", "monitor_sha256")}
    payload["snapshot_sha256"] = hashlib.sha256(json.dumps(identity_source, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    state_path = state_dir / "pass_state.json"
    prior = load(state_path) if state_path.is_file() else {}
    rows = [record["rows"] for record in payload["chain_snapshots"]]
    hashes = [record["sha256"] for record in payload["chain_snapshots"]]
    current = {"rows": rows, "hashes": hashes, "snapshot_sha256": payload["snapshot_sha256"]}
    eligibility = None
    if not all(payload["policy_gates"].values()):
        payload.update(status="AUTHORITATIVE_CONTINUE", consecutive_passes=0, stop_eligible=False)
        state = {"first_pass": None, "last_status": payload["status"]}
    elif not prior.get("first_pass"):
        payload.update(status="AUTHORITATIVE_PASS_1", consecutive_passes=1, stop_eligible=False)
        state = {"first_pass": current, "last_status": payload["status"]}
    else:
        first = prior["first_pass"]
        growth = [now - before for now, before in zip(rows, first["rows"])]
        separated = min(growth) >= policy["repeated_pass"]["minimum_new_complete_rows_per_chain"] and all(a != b for a, b in zip(hashes, first["hashes"]))
        if separated:
            payload.update(status="STOP_ELIGIBLE", consecutive_passes=2, stop_eligible=True, row_growth_since_first_pass=growth)
            eligibility = {"schema_version": "wp7-fs7-stop-eligibility-v1", "setting": setting, "policy_sha256": sha(POLICY), "first_pass": first, "second_pass": current}
            state = {**prior, "second_pass": current, "last_status": payload["status"]}
        else:
            payload.update(status="AUTHORITATIVE_PASS_WAITING_FOR_SEPARATION", consecutive_passes=1, stop_eligible=False, row_growth_since_first_pass=growth)
            state = {**prior, "last_status": payload["status"]}
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    atomic_write_json(state_dir / "snapshots" / f"{stamp}.json", payload)
    atomic_write_json(state_dir / "latest.json", payload)
    atomic_write_json(state_path, state)
    if eligibility:
        atomic_write_json(state_dir / "stop_eligible.json", eligibility)
    return payload


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(); parser.add_argument("setting", choices=SETTINGS); args = parser.parse_args()
    result = evaluate(args.setting)
    print(json.dumps({"setting": args.setting, "status": result["status"], "gates": result["policy_gates"]}, sort_keys=True))
