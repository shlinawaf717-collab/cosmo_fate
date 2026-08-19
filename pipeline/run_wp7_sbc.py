#!/usr/bin/env python3
"""Run the frozen 50-dataset WP7 SBC campaign, three datasets at a time."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import signal
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from pipeline.audit_wp4_f0_reproduction import atomic_write_json
from pipeline.monitor_wp7 import ROOT
from pipeline.monitor_wp7_sbc import SBC_ROOT, chain_paths, collect


PLAN = SBC_ROOT / "inference_plan.json"
ACTIVATION = SBC_ROOT / "sbc_activation.json"
AUTHORIZATION = SBC_ROOT / "WP7_SBC_STARTED.json"
EVENTS = SBC_ROOT / "sbc_driver_events.jsonl"
LOCK = SBC_ROOT / "sbc_driver.lock"
POLL_SECONDS = 300
SEPARATION_ROWS = 160


def _append(event: dict) -> None:
    payload = {**event, "timestamp_utc": datetime.now(timezone.utc).isoformat()}
    descriptor = os.open(EVENTS, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    try:
        os.write(descriptor, (json.dumps(payload, sort_keys=True) + "\n").encode()); os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _closed(index: int) -> bool:
    path = SBC_ROOT / f"s{index:03d}/convergence_audit.json"
    return path.is_file() and json.loads(path.read_text()).get("status") == "PASS"


def _launch(config: Path) -> subprocess.Popen:
    checkpoint = config.parent / "chain.checkpoint"
    command = [str(ROOT / ".venv/bin/cobaya-run"), str(config), "--no-mpi", "--resume" if checkpoint.exists() else "--force"]
    env = os.environ.copy(); env["PYTHONPATH"] = str(ROOT)
    env.update({name: "1" for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")})
    log = (config.parent / "run.log").open("a")
    process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
    process._wp7_log = log
    return process


def _stop(processes: list[subprocess.Popen]) -> None:
    for process in processes:
        os.kill(process.pid, signal.SIGSTOP)
    time.sleep(2)


def _terminate(processes: list[subprocess.Popen]) -> None:
    for process in processes:
        if process.poll() is None:
            process.terminate(); os.kill(process.pid, signal.SIGCONT)
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline and any(process.poll() is None for process in processes):
        time.sleep(0.2)
    for process in processes:
        if process.poll() is None: process.kill()
        process._wp7_log.close()


def run_dataset(index: int, records: list[dict]) -> dict:
    if _closed(index):
        return {"index": index, "status": "SKIP_CLOSED"}
    configs = [ROOT / row["config"] for row in sorted(records, key=lambda row: row["chain_index"])]
    processes = [_launch(config) for config in configs]
    _append({"event": "sbc_dataset_start", "index": index, "pids": [process.pid for process in processes]})
    first_pass = None
    try:
        while True:
            if any(process.poll() is not None for process in processes):
                raise RuntimeError(f"SBC {index}: chain exited before convergence transaction")
            try:
                diagnostics = collect(index)
            except (FileNotFoundError, ValueError):
                time.sleep(POLL_SECONDS); continue
            rows = [row["rows"] for row in diagnostics["chain_snapshots"]]
            hashes = [row["sha256"] for row in diagnostics["chain_snapshots"]]
            if diagnostics["status"] != "PASS":
                first_pass = None
            elif first_pass is None:
                first_pass = {"rows": rows, "hashes": hashes}
            else:
                growth = [now - before for now, before in zip(rows, first_pass["rows"])]
                if min(growth) >= SEPARATION_ROWS and all(a != b for a, b in zip(hashes, first_pass["hashes"])):
                    _stop(processes)
                    sizes = [path.stat().st_size for path in chain_paths(index)]; time.sleep(2)
                    if sizes != [path.stat().st_size for path in chain_paths(index)]:
                        for process in processes: os.kill(process.pid, signal.SIGCONT)
                        first_pass = None; continue
                    final = collect(index)
                    if final["status"] != "PASS":
                        for process in processes: os.kill(process.pid, signal.SIGCONT)
                        first_pass = None; continue
                    audit = {"schema_version": "wp7-fs7-sbc-convergence-audit-v1", "created_at_utc": datetime.now(timezone.utc).isoformat(), "status": "PASS", "dataset_index": index, "first_pass": first_pass, "row_growth": growth, "stable_sizes": sizes, "final_diagnostics": final, "truth_rank_calculated": False}
                    atomic_write_json(SBC_ROOT / f"s{index:03d}/convergence_audit.json", audit)
                    _terminate(processes)
                    _append({"event": "sbc_dataset_closed", "index": index})
                    return {"index": index, "status": "PASS"}
            time.sleep(POLL_SECONDS)
    except Exception:
        for process in processes:
            if process.poll() is None:
                try: os.kill(process.pid, signal.SIGCONT)
                except ProcessLookupError: pass
        _terminate(processes)
        raise


def validate() -> tuple[dict, dict]:
    plan, activation, authorization = [json.loads(path.read_text()) for path in (PLAN, ACTIVATION, AUTHORIZATION)]
    if activation["status"] != "READY_TO_START_WP7_SBC" or not authorization.get("production_authorized"):
        raise RuntimeError("WP7 SBC is not authorized")
    if authorization["plan_sha256"] != hashlib.sha256(PLAN.read_bytes()).hexdigest() or authorization["activation_sha256"] != hashlib.sha256(ACTIVATION.read_bytes()).hexdigest():
        raise RuntimeError("WP7 SBC authorization hash mismatch")
    return plan, activation


def main() -> int:
    plan, _ = validate(); grouped = {index: [] for index in range(1, 51)}
    for row in plan["chains"]: grouped[row["dataset_index"]].append(row)
    with LOCK.open("w") as lock:
        try: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc: raise RuntimeError("another WP7 SBC driver holds the lock") from exc
        lock.write(str(os.getpid()) + "\n"); lock.flush()
        with ThreadPoolExecutor(max_workers=3) as executor:
            results = [future.result() for future in as_completed([executor.submit(run_dataset, index, grouped[index]) for index in grouped])]
    return 0 if all(row["status"] in {"PASS", "SKIP_CLOSED"} for row in results) else 1


if __name__ == "__main__": raise SystemExit(main())
