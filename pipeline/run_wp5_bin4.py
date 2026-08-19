#!/usr/bin/env python3
"""Launch or resume the frozen 12-chain WP5 campaign with eight workers."""

from __future__ import annotations

import fcntl
import json
import os
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from pipeline.evaluate_wp5_external_stop import ROOT, SYSTEM_ROOT, validate


LOCK = SYSTEM_ROOT / "driver.lock"
EVENTS = SYSTEM_ROOT / "driver_events.jsonl"
PRINT_LOCK = threading.Lock()


def append(event: dict) -> None:
    payload={**event,"timestamp_utc":datetime.now(timezone.utc).isoformat()}
    with PRINT_LOCK:
        fd=os.open(EVENTS,os.O_WRONLY|os.O_CREAT|os.O_APPEND,0o644)
        try: os.write(fd,(json.dumps(payload,sort_keys=True)+"\n").encode()); os.fsync(fd)
        finally: os.close(fd)
        print(json.dumps(payload,sort_keys=True),flush=True)


def width_closed(width_tag: str) -> bool:
    path=SYSTEM_ROOT/f"delta_{width_tag}/external_monitor/final_stop_audit.json"
    if not path.exists(): return False
    payload=json.loads(path.read_text())
    return payload.get("status") in {"EXTERNALLY_STOPPED","EXTERNALLY_STOPPED_WITH_EXIT_WARNING"} and payload.get("post_termination_gates_pass") is True


def run_chain(record: dict) -> dict:
    width=record["width_tag"]; chain=record["chain"]
    if width_closed(width):
        result={"event":"chain_skip_closed_width","width_tag":width,"chain":chain,"returncode":None}
        append(result); return result
    config=ROOT/record["config"]; directory=config.parent
    checkpoint=directory/"chain.checkpoint"
    command=[str(ROOT/".venv/bin/cobaya-run"),str(config),"--no-mpi"]
    if checkpoint.exists(): command.append("--resume")
    env=os.environ.copy(); env.update({name:"1" for name in (
        "OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","NUMEXPR_NUM_THREADS","VECLIB_MAXIMUM_THREADS")})
    env["PYTHONPATH"]=str(ROOT)
    append({"event":"chain_start","width_tag":width,"chain":chain,"resume":checkpoint.exists()})
    with (directory/"run.log").open("a",encoding="utf-8") as log:
        completed=subprocess.run(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,check=False)
    result={"event":"chain_exit","width_tag":width,"chain":chain,"returncode":completed.returncode}
    append(result); return result


def main() -> int:
    plan_path=SYSTEM_ROOT/"run_plan.json"; plan=json.loads(plan_path.read_text())
    validate()
    if plan.get("status")!="FROZEN_BEFORE_WP5_PRODUCTION" or plan.get("max_parallel_chains")!=8:
        raise RuntimeError("WP5 run plan is not authoritative")
    with LOCK.open("w",encoding="utf-8") as lock:
        try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError: raise RuntimeError("another WP5 driver holds the lock")
        lock.write(str(os.getpid())+"\n"); lock.flush()
        append({"event":"driver_start","pid":os.getpid(),"jobs":8,"chains":12})
        with ThreadPoolExecutor(max_workers=8) as executor:
            results=[future.result() for future in as_completed(
                [executor.submit(run_chain,record) for record in plan["chains"]])]
        success=all(width_closed(tag) for tag in ("0p005","0p01","0p02"))
        append({"event":"driver_exit","success":success,"results":len(results)})
        return 0 if success else 1


if __name__=="__main__": raise SystemExit(main())
