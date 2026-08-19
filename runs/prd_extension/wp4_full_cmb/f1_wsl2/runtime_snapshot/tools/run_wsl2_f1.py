#!/usr/bin/env python3
"""Launch or resume the frozen four-chain WSL2 F1 run."""

from __future__ import annotations

import fcntl
import json
import os
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUN_ROOT = ROOT / "work/f1"
LOCK = RUN_ROOT / "driver.lock"
EVENTS = RUN_ROOT / "driver_events.jsonl"
PRINT_LOCK = threading.Lock()


def append(event: dict) -> None:
    payload = {**event, "timestamp_utc": datetime.now(timezone.utc).isoformat()}
    with PRINT_LOCK:
        fd = os.open(EVENTS, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
        try:
            os.write(fd, (json.dumps(payload, sort_keys=True) + "\n").encode()); os.fsync(fd)
        finally: os.close(fd)
        print(json.dumps(payload, sort_keys=True), flush=True)


def run_chain(ordinal: int) -> dict:
    directory = RUN_ROOT / f"c{ordinal}"
    command = [str(ROOT / ".venv/bin/cobaya-run"), str(directory / "run.yaml"), "--no-mpi"]
    checkpoint = directory / "chain.checkpoint"
    if checkpoint.exists(): command.append("--resume")
    env = os.environ.copy()
    env.update({name: "1" for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")})
    append({"event": "chain_start", "chain": ordinal, "resume": checkpoint.exists()})
    with (directory / "run.log").open("a", encoding="utf-8") as log:
        result = subprocess.run(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, check=False)
    record = {"event": "chain_exit", "chain": ordinal, "returncode": result.returncode}
    append(record); return record


def main() -> int:
    from tools.evaluate_wsl2_f1 import validate
    validate()
    preflight = json.loads((ROOT / "work/preflight/PREFLIGHT_GO.json").read_text())
    authorization = json.loads((ROOT / "work/f1/WSL2_PRODUCTION_STARTED.json").read_text())
    if preflight.get("status") != "PASS" or not authorization.get("production_authorized"):
        raise RuntimeError("WSL2 production is not authorized")
    RUN_ROOT.mkdir(parents=True, exist_ok=True)
    with LOCK.open("w", encoding="utf-8") as lock:
        try: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError: raise RuntimeError("another WSL2 F1 driver holds the lock")
        lock.write(str(os.getpid()) + "\n"); lock.flush()
        append({"event": "driver_start", "jobs": 4, "pid": os.getpid()})
        with ThreadPoolExecutor(max_workers=4) as executor:
            results = [future.result() for future in as_completed([executor.submit(run_chain, i) for i in range(1,5)])]
        success = all(item["returncode"] == 0 for item in results)
        append({"event": "driver_exit", "success": success})
        return 0 if success else 1


if __name__ == "__main__": raise SystemExit(main())
