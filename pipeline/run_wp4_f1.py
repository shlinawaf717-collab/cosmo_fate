#!/usr/bin/env python3
"""Prepare, launch, and safely resume four independent WP4 F1 chains."""

from __future__ import annotations

import argparse
import copy
import fcntl
import json
import os
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import yaml

from pipeline.build_wp4_f1_config import validate_config
from pipeline.wp4_preflight import ROOT, WP4_ROOT, sha256_file


CONFIG = ROOT / "pipeline/wp4_f1.yaml"
PROPOSAL = WP4_ROOT / "f1_proposal.covmat"
PROPOSAL_AUDIT = WP4_ROOT / "f1_proposal_audit.json"
F0_REPRODUCTION_AUDIT = WP4_ROOT / "f0_reproduction_audit.json"
INPUT_MANIFEST = WP4_ROOT / "input_manifest.json"
RUN_ROOT = WP4_ROOT / "f1"
RUN_PLAN = RUN_ROOT / "run_plan.json"
EVENTS = RUN_ROOT / "driver_events.jsonl"
LOCK = RUN_ROOT / "driver.lock"
CHAIN_SEEDS = (4511, 4512, 4513, 4514)
PRINT_LOCK = threading.Lock()


class WP4F1DriverError(RuntimeError):
    """Raised when F1 production would violate the frozen setup."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _chain_root(ordinal: int) -> Path:
    return RUN_ROOT / f"c{ordinal}"


def _validated_inputs() -> None:
    f0 = json.loads(F0_REPRODUCTION_AUDIT.read_text(encoding="utf-8"))
    if f0.get("status") != "PASS":
        raise WP4F1DriverError("F0 reproduction gate has not passed")
    proposal = json.loads(PROPOSAL_AUDIT.read_text(encoding="utf-8"))
    if proposal.get("status") != "PASS":
        raise WP4F1DriverError("F1 proposal audit has not passed")
    if proposal["covariance"]["sha256"] != sha256_file(PROPOSAL):
        raise WP4F1DriverError("F1 proposal hash differs from its audit")
    validate_config(yaml.safe_load(CONFIG.read_text(encoding="utf-8")))


def build_chain_config(ordinal: int, seed: int) -> dict:
    config = copy.deepcopy(yaml.safe_load(CONFIG.read_text(encoding="utf-8")))
    chain_root = _chain_root(ordinal).resolve()
    config["packages_path"] = str((ROOT / "data/cobaya_packages").resolve())
    config["theory"]["camb"]["path"] = "global"
    config["sampler"]["mcmc"]["covmat"] = str(PROPOSAL.resolve())
    config["sampler"]["mcmc"]["seed"] = seed
    config["output"] = str(chain_root / "chain")
    return config


def _expected_plan(chains: list[dict]) -> dict:
    return {
        "schema_version": "wp4-f1-run-plan-v1",
        "status": "FROZEN_BEFORE_PRODUCTION",
        "model": "flat CPL+P1 F1 primary full-CMB fate run",
        "data_change_from_f0": "Pantheon+ replaced by Pantheon+SH0ES",
        "jobs": len(CHAIN_SEEDS),
        "chain_seeds": list(CHAIN_SEEDS),
        "thread_limits_per_chain": 1,
        "execution_mode": "four independent no-MPI chains",
        "base_config": {
            "path": str(CONFIG.relative_to(ROOT)),
            "sha256": sha256_file(CONFIG),
        },
        "input_manifest": {
            "path": str(INPUT_MANIFEST.relative_to(ROOT)),
            "sha256": sha256_file(INPUT_MANIFEST),
        },
        "proposal_covariance": {
            "path": str(PROPOSAL.relative_to(ROOT)),
            "sha256": sha256_file(PROPOSAL),
            "scope": "17 F0 parameters; Mb uses its frozen scalar proposal",
        },
        "target_prior": "CPL+P1 with w+wa<0",
        "convergence_authority": "prospective external F1 policy",
        "sampling_endpoint_inspection_during_run": False,
        "fate_calculation_during_sampling": False,
        "chains": chains,
    }


def prepare() -> dict:
    _validated_inputs()
    RUN_ROOT.mkdir(parents=True, exist_ok=True)
    chains = []
    for ordinal, seed in enumerate(CHAIN_SEEDS, start=1):
        chain_root = _chain_root(ordinal)
        chain_root.mkdir(parents=True, exist_ok=True)
        run_yaml = chain_root / "run.yaml"
        expected_text = yaml.safe_dump(
            build_chain_config(ordinal, seed), sort_keys=False, width=100
        )
        if run_yaml.exists() and run_yaml.read_text(encoding="utf-8") != expected_text:
            raise WP4F1DriverError(f"frozen run YAML differs: {run_yaml}")
        if not run_yaml.exists():
            run_yaml.write_text(expected_text, encoding="utf-8")
        chains.append(
            {
                "chain": ordinal,
                "seed": seed,
                "run_yaml": str(run_yaml.relative_to(ROOT)),
                "run_yaml_sha256": sha256_file(run_yaml),
                "output_prefix": str((chain_root / "chain").relative_to(ROOT)),
            }
        )
    expected = _expected_plan(chains)
    if RUN_PLAN.exists():
        existing = json.loads(RUN_PLAN.read_text(encoding="utf-8"))
        if existing != expected:
            raise WP4F1DriverError("existing F1 run plan differs from frozen plan")
    else:
        RUN_PLAN.write_text(
            json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    return expected


def _append_event(record: dict) -> None:
    payload = {**record, "timestamp": _utc_now()}
    with PRINT_LOCK:
        with EVENTS.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(payload, sort_keys=True) + "\n")
        print(json.dumps(payload, sort_keys=True), flush=True)


def _run_chain(ordinal: int) -> dict:
    chain_root = _chain_root(ordinal)
    run_yaml = chain_root / "run.yaml"
    checkpoint = chain_root / "chain.checkpoint"
    command = [str(ROOT / ".venv/bin/cobaya-run"), str(run_yaml), "--no-mpi"]
    if checkpoint.exists():
        command.append("--resume")
    environment = os.environ.copy()
    environment.update(
        {
            "PYTHONPATH": str(ROOT),
            "OMP_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "NUMEXPR_NUM_THREADS": "1",
            "VECLIB_MAXIMUM_THREADS": "1",
        }
    )
    _append_event({"event": "chain_start", "chain": ordinal, "resume": checkpoint.exists()})
    with (chain_root / "run.log").open("a", encoding="utf-8") as log:
        completed = subprocess.run(
            command, cwd=ROOT, env=environment, stdout=log,
            stderr=subprocess.STDOUT, check=False,
        )
    record = {"event": "chain_exit", "chain": ordinal, "returncode": completed.returncode}
    _append_event(record)
    return record


def run(jobs: int) -> int:
    if jobs != len(CHAIN_SEEDS):
        raise WP4F1DriverError(f"F1 is frozen at {len(CHAIN_SEEDS)} jobs")
    prepare()
    with LOCK.open("w", encoding="utf-8") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise WP4F1DriverError("another WP4 F1 driver holds the lock") from exc
        lock.write(str(os.getpid()) + "\n")
        lock.flush()
        _append_event({"event": "driver_start", "jobs": jobs, "pid": os.getpid()})
        with ThreadPoolExecutor(max_workers=jobs) as executor:
            futures = {
                executor.submit(_run_chain, ordinal): ordinal
                for ordinal in range(1, len(CHAIN_SEEDS) + 1)
            }
            results = [future.result() for future in as_completed(futures)]
        success = all(record["returncode"] == 0 for record in results)
        _append_event({"event": "driver_exit", "success": success})
        return 0 if success else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=int, default=len(CHAIN_SEEDS))
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args(argv)
    plan = prepare()
    if args.prepare_only:
        print(f"prepared {RUN_PLAN}: {plan['jobs']} chains")
        return 0
    return run(args.jobs)


if __name__ == "__main__":
    raise SystemExit(main())
