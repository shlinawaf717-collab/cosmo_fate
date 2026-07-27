#!/usr/bin/env python3
"""Prepare, launch, and safely resume four independent WP4 F0 MCMC chains.

The driver never computes fate classifications or aggregate scientific
endpoints.  Each chain has a fixed seed and isolated output directory.
"""

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

from pipeline.wp4_preflight import ROOT, WP4_ROOT, sha256_file


CONFIG = ROOT / "pipeline" / "wp4_f0.yaml"
PROPOSAL = WP4_ROOT / "f0_proposal.covmat"
INPUT_MANIFEST = WP4_ROOT / "input_manifest.json"
PREFLIGHT = WP4_ROOT / "preflight.json"
RUN_ROOT = WP4_ROOT / "f0"
RUN_PLAN = RUN_ROOT / "run_plan.json"
EVENTS = RUN_ROOT / "driver_events.jsonl"
LOCK = RUN_ROOT / "driver.lock"
CHAIN_SEEDS = (4411, 4412, 4413, 4414)
PRINT_LOCK = threading.Lock()


class WP4F0DriverError(RuntimeError):
    """Raised when production would violate the audited F0 setup."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _chain_root(ordinal: int) -> Path:
    return RUN_ROOT / f"c{ordinal}"


def build_chain_config(ordinal: int, seed: int) -> dict:
    base = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    config = copy.deepcopy(base)
    chain_root = _chain_root(ordinal).resolve()
    config["packages_path"] = str((ROOT / "data/cobaya_packages").resolve())
    config["theory"]["camb"]["path"] = "global"
    config["sampler"]["mcmc"]["covmat"] = str(PROPOSAL.resolve())
    config["sampler"]["mcmc"]["seed"] = seed
    config["output"] = str(chain_root / "chain")
    return config


def _validated_preflight() -> dict:
    report = json.loads(PREFLIGHT.read_text(encoding="utf-8"))
    if report.get("status") != "READY_FOR_F0_REPRODUCTION":
        raise WP4F0DriverError(f"WP4 preflight is not ready: {report.get('status')}")
    if report.get("inference_permitted") is not True:
        raise WP4F0DriverError("WP4 preflight does not permit F0 inference")
    if report.get("fate_calculation_performed") is not False:
        raise WP4F0DriverError("unexpected fate calculation in preflight")
    return report


def prepare() -> dict:
    _validated_preflight()
    RUN_ROOT.mkdir(parents=True, exist_ok=True)
    chains = []
    for ordinal, seed in enumerate(CHAIN_SEEDS, start=1):
        chain_root = _chain_root(ordinal)
        chain_root.mkdir(parents=True, exist_ok=True)
        run_yaml = chain_root / "run.yaml"
        run_yaml.write_text(
            yaml.safe_dump(
                build_chain_config(ordinal, seed),
                sort_keys=False,
                width=100,
            ),
            encoding="utf-8",
        )
        chains.append(
            {
                "chain": ordinal,
                "seed": seed,
                "run_yaml": str(run_yaml.relative_to(ROOT)),
                "run_yaml_sha256": sha256_file(run_yaml),
                "output_prefix": str((chain_root / "chain").relative_to(ROOT)),
            }
        )
    plan = {
        "schema_version": "wp4-f0-run-plan-v1",
        "status": "FROZEN_BEFORE_PRODUCTION",
        "model": "flat CPL F0 reproduction",
        "jobs": len(CHAIN_SEEDS),
        "chain_seeds": list(CHAIN_SEEDS),
        "thread_limits_per_chain": 1,
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
        },
        "convergence_gates": {
            "Rminus1_exclusive": 0.01,
            "bulk_ess_minimum": 1000,
            "tail_ess_w0_wa_minimum": 400,
        },
        "sampling_endpoint_inspection_during_run": False,
        "fate_calculation_during_F0": False,
        "chains": chains,
    }
    RUN_PLAN.write_text(
        json.dumps(plan, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return plan


def _checkpoint_converged(path: Path) -> bool:
    if not path.is_file():
        return False
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return payload.get("sampler", {}).get("mcmc", {}).get("converged") is True


def _append_event(record: dict) -> None:
    payload = dict(record)
    payload["timestamp"] = _utc_now()
    with PRINT_LOCK:
        with EVENTS.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(payload, sort_keys=True) + "\n")
        print(json.dumps(payload, sort_keys=True), flush=True)


def _run_chain(ordinal: int) -> dict:
    chain_root = _chain_root(ordinal)
    run_yaml = chain_root / "run.yaml"
    checkpoint = chain_root / "chain.checkpoint"
    if _checkpoint_converged(checkpoint):
        record = {"event": "skip_converged", "chain": ordinal, "returncode": 0}
        _append_event(record)
        return record

    command = [
        str(ROOT / ".venv/bin/cobaya-run"),
        str(run_yaml),
        "--no-mpi",
    ]
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
    _append_event(
        {
            "event": "chain_start",
            "chain": ordinal,
            "resume": checkpoint.exists(),
        }
    )
    with (chain_root / "run.log").open("a", encoding="utf-8") as log:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            env=environment,
            stdout=log,
            stderr=subprocess.STDOUT,
            check=False,
        )
    record = {
        "event": "chain_exit",
        "chain": ordinal,
        "returncode": completed.returncode,
        "converged": _checkpoint_converged(checkpoint),
    }
    _append_event(record)
    return record


def run(jobs: int) -> int:
    if jobs != len(CHAIN_SEEDS):
        raise WP4F0DriverError(
            f"WP4 F0 production is frozen at {len(CHAIN_SEEDS)} jobs"
        )
    prepare()
    with LOCK.open("w", encoding="utf-8") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise WP4F0DriverError("another WP4 F0 driver already holds the lock") from exc
        lock.write(str(os.getpid()) + "\n")
        lock.flush()
        _append_event({"event": "driver_start", "jobs": jobs, "pid": os.getpid()})
        results = []
        with ThreadPoolExecutor(max_workers=jobs) as executor:
            futures = {
                executor.submit(_run_chain, ordinal): ordinal
                for ordinal in range(1, len(CHAIN_SEEDS) + 1)
            }
            for future in as_completed(futures):
                results.append(future.result())
        success = all(
            record.get("returncode") == 0 and record.get("converged") is not False
            for record in results
        )
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
