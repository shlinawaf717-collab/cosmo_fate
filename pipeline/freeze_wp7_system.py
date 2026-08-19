#!/usr/bin/env python3
"""Materialize and hash the five-setting, twenty-chain WP7 real-data system."""

from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path

from cobaya.yaml import yaml_dump, yaml_load_file

from pipeline.audit_wp4_f0_reproduction import atomic_write_json, sha256_file
from pipeline.build_wp7_configs import ROOT, SETTINGS


SYSTEM = ROOT / "runs/prd_extension/wp7/production_system"
PLAN = SYSTEM / "run_plan.json"
ACTIVATION = SYSTEM / "activation.json"
POLICY = ROOT / "plan/wp7_execution_protocol.json"
SMOKE = SYSTEM / "system_smoke_audit.json"
CODE = (
    "pipeline/wp7_fs7.py", "pipeline/wparams.py", "pipeline/bgtheory.py",
    "pipeline/monitor_wp7.py", "pipeline/run_wp7.py", "pipeline/evaluate_wp7_stop.py",
    "pipeline/finalize_wp7.py", "pipeline/run_wp7_controller.py",
    "pipeline/authorize_wp7.py", "pipeline/run_wp7_system_smoke.py",
)


def _record(path: Path) -> dict:
    return {"path": str(path.relative_to(ROOT)), "sha256": sha256_file(path)}


def freeze() -> dict:
    policy = json.loads(POLICY.read_text())
    if policy["status"] != "FROZEN_BEFORE_WP7_POSTERIOR_SAMPLING":
        raise RuntimeError("WP7 execution protocol is not frozen")
    if PLAN.is_file():
        plan = json.loads(PLAN.read_text())
        for chain in plan["chains"]:
            if sha256_file(ROOT / chain["config"]) != chain["config_sha256"]:
                raise RuntimeError("WP7 frozen real-data config hash mismatch")
    else:
        if list(SYSTEM.glob("**/chain.*.txt")):
            raise RuntimeError("refusing to freeze over WP7 samples")
        chains = []
        for tag, setting in policy["settings"].items():
            base_path = ROOT / f"runs/prd_extension/wp7/configs/fs7_{tag}.yaml"
            base = yaml_load_file(str(base_path))
            for index, seed in enumerate(setting["chain_seeds"], 1):
                info = copy.deepcopy(base)
                info["packages_path"] = str(ROOT / "data/cobaya_packages")
                mcmc = info["sampler"]["mcmc"]
                mcmc.update(seed=seed, Rminus1_stop=1.0e-6, Rminus1_cl_stop=1.0e-6,
                            max_samples=float("inf"), measure_speeds=True)
                directory = SYSTEM / tag / f"c{index}"
                directory.mkdir(parents=True, exist_ok=True)
                info["output"] = str(directory / "chain")
                info["wp7_metadata"] = {"role": "WP7 real-data production", "setting": tag, "chain": index}
                config = directory / "run.yaml"
                config.write_text(yaml_dump(info), encoding="utf-8")
                chains.append({
                    "setting": tag, "chain": index, "seed": seed,
                    "config": str(config.relative_to(ROOT)), "config_sha256": sha256_file(config),
                    "output_prefix": str((directory / "chain").relative_to(ROOT)),
                })
        plan = {
            "schema_version": "wp7-fs7-real-data-run-plan-v1",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "status": "FROZEN_BEFORE_WP7_REAL_DATA_PRODUCTION",
            "settings": list(SETTINGS), "chains_per_setting": 4,
            "max_parallel_chains": policy["execution"]["max_parallel_chains"],
            "threads_per_chain": 1, "chains": chains,
            "policy": _record(POLICY),
            "information_plan": _record(ROOT / "runs/prd_extension/wp7/information_plan.json"),
            "fixed_point_preflight": _record(ROOT / "runs/prd_extension/wp7/fixed_point_preflight.json"),
            "truncation_preflight": _record(ROOT / "runs/prd_extension/wp7/truncation_preflight.json"),
            "posterior_or_fate_endpoint_read": False,
        }
        atomic_write_json(PLAN, plan)
    if SMOKE.is_file() and not ACTIVATION.is_file():
        smoke = json.loads(SMOKE.read_text())
        if smoke.get("status") != "PASS" or smoke.get("sampling_performed"):
            raise RuntimeError("WP7 production system smoke has not passed")
        activation = {
            "schema_version": "wp7-fs7-real-data-activation-v1",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "status": "READY_TO_START_WP7_REAL_DATA",
            "run_plan": _record(PLAN), "policy": _record(POLICY), "smoke": _record(SMOKE),
            "code": {name: _record(ROOT / name) for name in CODE},
            "posterior_samples_exist": False, "fate_endpoint_calculated": False,
        }
        atomic_write_json(ACTIVATION, activation)
    return plan


if __name__ == "__main__":
    result = freeze()
    print(json.dumps({"status": result["status"], "activation": ACTIVATION.is_file()}, sort_keys=True))
