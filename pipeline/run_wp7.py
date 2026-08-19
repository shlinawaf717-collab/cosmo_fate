#!/usr/bin/env python3
"""Launch or resume the frozen twenty-chain WP7 real-data campaign."""

from __future__ import annotations

import fcntl
import json
import os
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from pipeline.evaluate_wp7_stop import SYSTEM, validate
from pipeline.monitor_wp7 import ROOT, SETTINGS


LOCK = SYSTEM / "driver.lock"
EVENTS = SYSTEM / "driver_events.jsonl"
PRINT_LOCK = threading.Lock()


def append(event: dict) -> None:
    payload = {**event, "timestamp_utc": datetime.now(timezone.utc).isoformat()}
    with PRINT_LOCK:
        descriptor = os.open(EVENTS, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
        try:
            os.write(descriptor, (json.dumps(payload, sort_keys=True) + "\n").encode()); os.fsync(descriptor)
        finally:
            os.close(descriptor)
        print(json.dumps(payload, sort_keys=True), flush=True)


def setting_closed(setting: str) -> bool:
    path = SYSTEM / setting / "external_monitor/final_stop_audit.json"
    if not path.is_file():
        return False
    payload = json.loads(path.read_text())
    return payload.get("status", "").startswith("EXTERNALLY_STOPPED") and payload.get("post_termination_gates_pass") is True


def run_chain(record: dict) -> dict:
    setting, chain = record["setting"], record["chain"]
    if setting_closed(setting):
        result = {"event": "chain_skip_closed_setting", "setting": setting, "chain": chain, "returncode": None}; append(result); return result
    config = ROOT / record["config"]
    checkpoint = config.parent / "chain.checkpoint"
    command = [str(ROOT / ".venv/bin/cobaya-run"), str(config), "--no-mpi", "--resume" if checkpoint.exists() else "--force"]
    env = os.environ.copy(); env["PYTHONPATH"] = str(ROOT)
    env.update({name: "1" for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")})
    append({"event": "chain_start", "setting": setting, "chain": chain, "resume": checkpoint.exists()})
    with (config.parent / "run.log").open("a") as log:
        result = subprocess.run(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, check=False)
    payload = {"event": "chain_exit", "setting": setting, "chain": chain, "returncode": result.returncode}; append(payload); return payload


def main() -> int:
    plan_path = SYSTEM / "run_plan.json"; plan = json.loads(plan_path.read_text())
    _, activation = validate()
    authorization_path = SYSTEM / "WP7_PRODUCTION_STARTED.json"
    if not authorization_path.is_file():
        raise RuntimeError("WP7 production authorization is missing")
    authorization = json.loads(authorization_path.read_text())
    import hashlib
    if not authorization.get("production_authorized") or authorization["run_plan_sha256"] != hashlib.sha256(plan_path.read_bytes()).hexdigest() or authorization["activation_sha256"] != hashlib.sha256((SYSTEM / "activation.json").read_bytes()).hexdigest():
        raise RuntimeError("WP7 production authorization hash mismatch")
    with LOCK.open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("another WP7 driver holds the lock") from exc
        lock.write(str(os.getpid()) + "\n"); lock.flush()
        append({"event": "driver_start", "pid": os.getpid(), "jobs": plan["max_parallel_chains"], "chains": len(plan["chains"])})
        with ThreadPoolExecutor(max_workers=plan["max_parallel_chains"]) as executor:
            results = [future.result() for future in as_completed([executor.submit(run_chain, row) for row in plan["chains"]])]
        success = all(setting_closed(setting) for setting in SETTINGS)
        append({"event": "driver_exit", "success": success, "results": len(results)})
        return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
