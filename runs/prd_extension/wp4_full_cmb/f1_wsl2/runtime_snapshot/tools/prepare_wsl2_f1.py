#!/usr/bin/env python3
"""Create WSL2-local F1 configs, plan, policy, and activation hashes."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "payload"
RUN_ROOT = ROOT / "work/f1"
CONFIG = PROJECT / "pipeline/wp4_f1.yaml"
PROPOSAL = PROJECT / "runs/prd_extension/wp4_full_cmb/f1_proposal.covmat"
INPUT_MANIFEST = PROJECT / "runs/prd_extension/wp4_full_cmb/input_manifest.json"
POLICY_TEMPLATE = PROJECT / "plan/wp4_f1_external_convergence_policy.json"
RUN_PLAN = RUN_ROOT / "run_plan.json"
POLICY = RUN_ROOT / "external_convergence_policy.json"
ACTIVATION = RUN_ROOT / "external_stop_activation.json"
SEEDS = (4511, 4512, 4513, 4514)


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
        temporary = Path(handle.name)
    os.replace(temporary, path)


def record(path: Path) -> dict:
    return {"path": str(path.relative_to(ROOT)), "sha256": sha(path)}


def main() -> int:
    if list(RUN_ROOT.glob("c*/chain.*.txt")):
        raise RuntimeError("refusing to prepare over existing WSL2 F1 samples")
    base = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    chains = []
    for ordinal, seed in enumerate(SEEDS, 1):
        directory = RUN_ROOT / f"c{ordinal}"
        directory.mkdir(parents=True, exist_ok=True)
        info = copy.deepcopy(base)
        info["packages_path"] = str((PROJECT / "data/cobaya_packages").resolve())
        info["theory"]["camb"]["path"] = "global"
        info["sampler"]["mcmc"]["covmat"] = str(PROPOSAL.resolve())
        info["sampler"]["mcmc"]["seed"] = seed
        info["output"] = str((directory / "chain").resolve())
        path = directory / "run.yaml"
        path.write_text(yaml.safe_dump(info, sort_keys=False, width=100), encoding="utf-8")
        chains.append({
            "chain": ordinal, "seed": seed, "run_yaml": str(path.relative_to(ROOT)),
            "run_yaml_sha256": sha(path), "output_prefix": str((directory / "chain").relative_to(ROOT)),
        })
    plan = {
        "schema_version": "wp4-f1-wsl2-run-plan-v1",
        "status": "FROZEN_BEFORE_WSL2_PRODUCTION",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "model": "flat CPL+P1 F1 primary full-CMB fate run",
        "platform_role": "sole scientific F1 chain set after WSL2 production starts",
        "mac_samples_included": False,
        "jobs": 4, "chain_seeds": list(SEEDS), "thread_limits_per_chain": 1,
        "base_config": record(CONFIG), "proposal_covariance": record(PROPOSAL),
        "input_manifest": record(INPUT_MANIFEST), "chains": chains,
    }
    atomic_json(RUN_PLAN, plan)
    policy = json.loads(POLICY_TEMPLATE.read_text(encoding="utf-8"))
    policy["status"] = "PROSPECTIVELY_FROZEN_BEFORE_WSL2_F1_PRODUCTION"
    policy["chains"] = [str((RUN_ROOT / f"c{i}/chain.1.txt").relative_to(ROOT)) for i in range(1, 5)]
    policy["stop_transaction"]["resume_command"] = "./wsl/05_start_f1.sh"
    policy["implementation"] = {
        **policy["implementation"],
        "statistics_path": "tools/monitor_wsl2_f1.py",
        "statistics_sha256": sha(ROOT / "tools/monitor_wsl2_f1.py"),
        "statistics_base_path": "payload/pipeline/monitor_wp4_f0.py",
        "statistics_base_sha256": sha(PROJECT / "pipeline/monitor_wp4_f0.py"),
    }
    atomic_json(POLICY, policy)
    components = {
        "policy": POLICY,
        "statistics": ROOT / "tools/monitor_wsl2_f1.py",
        "statistics_base": PROJECT / "pipeline/monitor_wp4_f0.py",
        "evaluator": ROOT / "tools/evaluate_wsl2_f1.py",
        "finalizer": ROOT / "tools/finalize_wsl2_f1.py",
        "controller": ROOT / "tools/controller_wsl2_f1.py",
        "driver": ROOT / "tools/run_wsl2_f1.py",
    }
    runtime = {"run_plan": RUN_PLAN, "base_config": CONFIG, "proposal_covariance": PROPOSAL, "input_manifest": INPUT_MANIFEST}
    runtime.update({f"chain_{item['chain']}_run_yaml": ROOT / item["run_yaml"] for item in chains})
    activation = {
        "schema_version": "wp4-f1-wsl2-activation-v1",
        "status": "ACTIVE_BEFORE_WSL2_PRODUCTION",
        "activated_at_utc": datetime.now(timezone.utc).isoformat(),
        "hashes": {name: record(path) for name, path in components.items()},
        "runtime_hashes": {name: record(path) for name, path in runtime.items()},
        "preflight_hashes": {
            path.name: record(path)
            for path in sorted((ROOT / "work/preflight").glob("*.json"))
            if path.name != "PREFLIGHT_GO.json"
        },
        "mac_samples_included": False,
        "scientific_endpoints_inspected": False,
    }
    atomic_json(ACTIVATION, activation)
    print(json.dumps({"status": activation["status"], "run_plan": str(RUN_PLAN)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
