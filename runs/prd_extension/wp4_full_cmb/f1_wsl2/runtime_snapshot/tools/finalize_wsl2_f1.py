#!/usr/bin/env python3
"""Pause, audit, and transactionally stop an eligible WSL2 F1 run."""

from __future__ import annotations

import fcntl
import json
import os
import signal
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from tools.evaluate_wsl2_f1 import ACTIVATION, POLICY, ROOT, gates, load, sha, validate
from tools.monitor_wsl2_f1 import collect


RUN_ROOT = ROOT / "work/f1"
STATE = RUN_ROOT / "external_monitor"


def atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(payload, handle, indent=2, sort_keys=True); handle.write("\n")
        handle.flush(); os.fsync(handle.fileno()); temporary = Path(handle.name)
    os.replace(temporary, path)


def process_table() -> list[dict]:
    result = subprocess.run(["ps", "-axo", "pid=,ppid=,state=,command="], check=True, capture_output=True, text=True)
    rows = []
    for line in result.stdout.splitlines():
        parts = line.strip().split(None, 3)
        if len(parts) == 4: rows.append({"pid": int(parts[0]), "ppid": int(parts[1]), "state": parts[2], "command": parts[3]})
    return rows


def discover() -> tuple[dict, list[dict]]:
    pid = int((RUN_ROOT / "driver.lock").read_text().strip())
    table = process_table(); driver = {row["pid"]: row for row in table}.get(pid)
    if driver is None or "tools/run_wsl2_f1.py" not in driver["command"]: raise RuntimeError("frozen driver not alive")
    children = [row for row in table if row["ppid"] == pid and "cobaya-run" in row["command"] and "--no-mpi" in row["command"]]
    if len(children) != 4: raise RuntimeError(f"expected four Cobaya children, got {len(children)}")
    for i in range(1,5):
        if sum(f"work/f1/c{i}/run.yaml" in row["command"] for row in children) != 1: raise RuntimeError(f"child mapping failed c{i}")
    return driver, sorted(children, key=lambda x: x["command"])


def alive(pid: int) -> bool:
    try: os.kill(pid, 0); return True
    except ProcessLookupError: return False


def state(pid: int) -> str:
    return subprocess.run(["ps", "-o", "state=", "-p", str(pid)], capture_output=True, text=True).stdout.strip()


def wait_stopped(pids: list[int]) -> None:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if all(state(pid).startswith("T") for pid in pids): return
        time.sleep(.1)
    raise RuntimeError("children did not stop")


def wait_exit(pids: list[int], seconds: float) -> list[int]:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        pids = [pid for pid in pids if alive(pid)]
        if not pids: return []
        time.sleep(.2)
    return pids


def main() -> int:
    policy, activation = validate()
    eligibility = STATE / "stop_eligible.json"
    if not eligibility.exists(): raise RuntimeError("no stop eligibility")
    if load(eligibility)["policy_sha256"] != sha(POLICY): raise RuntimeError("eligibility hash mismatch")
    for name in ("finalizer", "controller"):
        record = activation["hashes"][name]
        if sha(ROOT / record["path"]) != record["sha256"]: raise RuntimeError(f"{name} hash mismatch")
    stopped = []; committed = False
    with (STATE / "finalizer.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        driver, children = discover(); pids = [x["pid"] for x in children]
        try:
            for pid in pids: os.kill(pid, signal.SIGSTOP); stopped.append(pid)
            wait_stopped(pids)
            paths = [ROOT / path for path in policy["chains"]]
            sizes = [path.stat().st_size for path in paths]; time.sleep(2)
            if sizes != [path.stat().st_size for path in paths]: raise RuntimeError("chain files changed while paused")
            diag = collect(paths); final_gates = gates(diag, policy)
            if not all(final_gates.values()): raise RuntimeError("paused snapshot failed")
            audit = {"schema_version": "wp4-f1-wsl2-final-stop-audit-v1", "created_at_utc": datetime.now(timezone.utc).isoformat(), "status": "COMMIT_TO_EXTERNAL_STOP", "policy_sha256": sha(POLICY), "activation_sha256": sha(ACTIVATION), "eligibility_sha256": sha(eligibility), "driver": driver, "children": children, "stable_sizes": sizes, "final_diagnostics": diag, "final_policy_gates": final_gates, "checkpoints_edited": False}
            audit_path = STATE / "final_stop_audit.json"; atomic(audit_path, audit); committed = True
            for pid in pids: os.kill(pid, signal.SIGTERM)
            for pid in pids:
                if alive(pid): os.kill(pid, signal.SIGCONT)
            remaining = wait_exit(pids, 20); escalated = list(remaining)
            for pid in remaining: os.kill(pid, signal.SIGKILL)
            remaining = wait_exit(remaining, 5); driver_remaining = wait_exit([driver["pid"]], 30)
            post = collect(paths); post_gates = gates(post, policy)
            audit.update({"completed_at_utc": datetime.now(timezone.utc).isoformat(), "status": "EXTERNALLY_STOPPED" if not remaining and not driver_remaining else "EXTERNALLY_STOPPED_WITH_EXIT_WARNING", "children_requiring_sigkill": escalated, "children_still_alive_after_sigkill": remaining, "driver_still_alive": driver_remaining, "post_termination_diagnostics": post, "post_termination_policy_gates": post_gates, "post_termination_gates_pass": all(post_gates.values())})
            atomic(audit_path, audit); print(json.dumps({"status": audit["status"]})); return 0
        except Exception as exc:
            if not committed:
                for pid in stopped:
                    if alive(pid): os.kill(pid, signal.SIGCONT)
                atomic(STATE / "final_stop_audit.json", {"status": "ABORTED_RESUMED", "error": f"{type(exc).__name__}: {exc}", "checkpoints_edited": False})
            raise


if __name__ == "__main__": raise SystemExit(main())
