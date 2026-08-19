#!/usr/bin/env python3
"""Final fail-closed audit immediately before WP7 start authorization."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from pipeline.audit_wp4_f0_reproduction import atomic_write_json, sha256_file
from pipeline.evaluate_wp7_stop import ACTIVATION as REAL_ACTIVATION, SYSTEM, validate
from pipeline.freeze_wp7_sbc_system import ACTIVATION as SBC_ACTIVATION, PLAN as SBC_PLAN
from pipeline.monitor_wp7 import ROOT
from pipeline.wp7_sbc import MANIFEST as SBC_INPUTS, audit as audit_sbc_inputs


OUTPUT = ROOT / "runs/prd_extension/wp7/production_readiness.json"
POLICY = ROOT / "plan/wp7_execution_protocol.json"
REAL_PLAN = SYSTEM / "run_plan.json"
REQUIRED = (
    ROOT / "runs/prd_extension/wp7_development/preflight.json",
    ROOT / "runs/prd_extension/wp7/fixed_point_preflight.json",
    ROOT / "runs/prd_extension/wp7/truncation_preflight.json",
    ROOT / "runs/prd_extension/wp7/smoke_audit.json",
    ROOT / "runs/prd_extension/wp7/information_plan.json",
    SYSTEM / "system_smoke_audit.json",
    SBC_INPUTS,
    SBC_PLAN,
    SBC_ACTIVATION,
)


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()


def audit(source_commit: str) -> dict:
    resolved_source_commit = git("rev-parse", source_commit)
    policy, real_activation = validate()
    sbc_activation = json.loads(SBC_ACTIVATION.read_text())
    sbc_inputs = audit_sbc_inputs()
    samples = sorted(
        path for path in (ROOT / "runs/prd_extension/wp7").rglob("chain.*.txt")
        if "system_smoke" not in path.parts and "development" not in path.parts
    )
    authorization_files = [SYSTEM / "WP7_PRODUCTION_STARTED.json", SBC_PLAN.parent / "WP7_SBC_STARTED.json"]
    checks = {
        "source_commit_is_head": git("rev-parse", "HEAD") == resolved_source_commit,
        "source_commit_is_on_remote_branch": git("merge-base", "--is-ancestor", resolved_source_commit, "@{u}") == "",
        "policy_frozen": policy["status"] == "FROZEN_BEFORE_WP7_POSTERIOR_SAMPLING",
        "real_activation_ready": real_activation["status"] == "READY_TO_START_WP7_REAL_DATA",
        "sbc_activation_ready": sbc_activation["status"] == "READY_TO_START_WP7_SBC",
        "sbc_inputs_pass": sbc_inputs["status"] == "PASS" and sbc_inputs["datasets"] == 50,
        "required_artifacts_present": all(path.is_file() for path in REQUIRED),
        "posterior_sample_files_absent": not samples,
        "start_authorizations_absent": not any(path.exists() for path in authorization_files),
        "real_chain_count_20": len(json.loads(REAL_PLAN.read_text())["chains"]) == 20,
        "sbc_chain_count_100": len(json.loads(SBC_PLAN.read_text())["chains"]) == 100,
    }
    payload = {
        "schema_version": "wp7-fs7-production-readiness-v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "READY_TO_AUTHORIZE_WP7" if all(checks.values()) else "NOT_READY",
        "source_git_commit": resolved_source_commit,
        "checks": checks,
        "real_plan": {"path": str(REAL_PLAN.relative_to(ROOT)), "sha256": sha256_file(REAL_PLAN)},
        "real_activation": {"path": str(REAL_ACTIVATION.relative_to(ROOT)), "sha256": sha256_file(REAL_ACTIVATION)},
        "sbc_plan": {"path": str(SBC_PLAN.relative_to(ROOT)), "sha256": sha256_file(SBC_PLAN)},
        "sbc_activation": {"path": str(SBC_ACTIVATION.relative_to(ROOT)), "sha256": sha256_file(SBC_ACTIVATION)},
        "posterior_sample_files": [str(path.relative_to(ROOT)) for path in samples],
        "fate_endpoint_calculated": False,
        "authorization_action_required": True,
    }
    atomic_write_json(OUTPUT, payload)
    if payload["status"] != "READY_TO_AUTHORIZE_WP7":
        raise RuntimeError(json.dumps(payload, indent=2))
    return payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--source-commit", required=True); args = parser.parse_args()
    print(json.dumps(audit(args.source_commit), indent=2, sort_keys=True))
