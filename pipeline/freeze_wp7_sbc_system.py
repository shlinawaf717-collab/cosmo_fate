#!/usr/bin/env python3
"""Smoke and activate the already frozen WP7 SBC inference plan."""

import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone

from cobaya.yaml import yaml_dump, yaml_load_file

from pipeline.audit_wp4_f0_reproduction import atomic_write_json, sha256_file
from pipeline.monitor_wp7 import ROOT
from pipeline.monitor_wp7_sbc import SBC_ROOT


PLAN = SBC_ROOT / "inference_plan.json"
SMOKE = SBC_ROOT / "sbc_system_smoke.json"
ACTIVATION = SBC_ROOT / "sbc_activation.json"
CODE = ("pipeline/wp7_sbc.py", "pipeline/monitor_wp7_sbc.py", "pipeline/run_wp7_sbc.py")


def freeze() -> dict:
    plan = json.loads(PLAN.read_text())
    for row in plan["chains"]:
        if sha256_file(ROOT / row["config"]) != row["config_sha256"]:
            raise RuntimeError("WP7 SBC config hash mismatch")
    if not SMOKE.is_file():
        source = ROOT / plan["chains"][0]["config"]
        info = yaml_load_file(str(source)); directory = SBC_ROOT / "system_smoke"; directory.mkdir(exist_ok=True)
        info["output"] = str(directory / "chain")
        config = directory / "smoke.yaml"; config.write_text(yaml_dump(info))
        env = os.environ.copy(); env["PYTHONPATH"] = str(ROOT)
        completed = subprocess.run([str(ROOT / ".venv/bin/cobaya-run"), "--test", str(config)], cwd=ROOT, env=env, capture_output=True, text=True)
        log = completed.stdout + "\n" + completed.stderr; (directory / "smoke.log").write_text(log)
        samples = list(directory.glob("chain.*.txt"))
        smoke = {"schema_version": "wp7-fs7-sbc-system-smoke-v1", "created_at_utc": datetime.now(timezone.utc).isoformat(), "status": "PASS" if completed.returncode == 0 and "Test initialization successful" in log and not samples else "FAIL", "sampling_performed": False, "truth_rank_calculated": False, "sample_files": [str(path) for path in samples]}
        atomic_write_json(SMOKE, smoke)
    smoke = json.loads(SMOKE.read_text())
    if smoke["status"] != "PASS": raise RuntimeError("WP7 SBC smoke failed")
    if not ACTIVATION.is_file():
        activation = {"schema_version": "wp7-fs7-sbc-activation-v1", "created_at_utc": datetime.now(timezone.utc).isoformat(), "status": "READY_TO_START_WP7_SBC", "plan_sha256": hashlib.sha256(PLAN.read_bytes()).hexdigest(), "smoke_sha256": hashlib.sha256(SMOKE.read_bytes()).hexdigest(), "code": {name: {"path": name, "sha256": sha256_file(ROOT / name)} for name in CODE}, "posterior_samples_exist": False, "sbc_rank_calculated": False}
        atomic_write_json(ACTIVATION, activation)
    return json.loads(ACTIVATION.read_text())


if __name__ == "__main__": print(json.dumps(freeze(), indent=2, sort_keys=True))
