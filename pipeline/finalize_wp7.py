#!/usr/bin/env python3
"""Transactionally stop one converged WP7 setting without touching others."""

from __future__ import annotations

import fcntl
import json
import os
import signal
import subprocess
import time
from datetime import datetime, timezone

from pipeline.audit_wp4_f0_reproduction import atomic_write_json
from pipeline.evaluate_wp7_stop import ACTIVATION, POLICY, SYSTEM, load, policy_gates, sha, validate
from pipeline.monitor_wp7 import SETTINGS, chain_paths, collect


def _process_table() -> list[dict]:
    result = subprocess.run(["ps", "-axo", "pid=,ppid=,state=,command="], capture_output=True, text=True, check=True)
    rows = []
    for line in result.stdout.splitlines():
        parts = line.strip().split(None, 3)
        if len(parts) == 4:
            rows.append({"pid": int(parts[0]), "ppid": int(parts[1]), "state": parts[2], "command": parts[3]})
    return rows


def _discover(setting: str) -> tuple[dict, list[dict]]:
    driver_pid = int((SYSTEM / "driver.lock").read_text().strip())
    rows = _process_table(); driver = {row["pid"]: row for row in rows}.get(driver_pid)
    if not driver or "run_wp7.py" not in driver["command"]:
        raise RuntimeError("WP7 driver is not alive")
    children = [row for row in rows if row["ppid"] == driver_pid and "cobaya-run" in row["command"] and f"production_system/{setting}/" in row["command"]]
    if len(children) != 4:
        raise RuntimeError(f"expected four {setting} children, got {len(children)}")
    for index in range(1, 5):
        if sum(f"/{setting}/c{index}/run.yaml" in row["command"] for row in children) != 1:
            raise RuntimeError(f"WP7 child mapping failed for {setting} c{index}")
    return driver, sorted(children, key=lambda row: row["command"])


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0); return True
    except ProcessLookupError:
        return False


def _wait_stopped(pids: list[int], seconds: float = 10) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        states = [subprocess.run(["ps", "-o", "state=", "-p", str(pid)], capture_output=True, text=True).stdout.strip() for pid in pids]
        if all(state.startswith("T") for state in states):
            return
        time.sleep(0.1)
    raise RuntimeError("WP7 children did not pause")


def _wait_exit(pids: list[int], seconds: float) -> list[int]:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        pids = [pid for pid in pids if _alive(pid)]
        if not pids:
            return []
        time.sleep(0.2)
    return pids


def finalize(setting: str) -> dict:
    if setting not in SETTINGS:
        raise ValueError(setting)
    policy, _ = validate(); state_dir = SYSTEM / setting / "external_monitor"
    eligibility = state_dir / "stop_eligible.json"
    if not eligibility.is_file() or load(eligibility)["policy_sha256"] != sha(POLICY):
        raise RuntimeError("WP7 stop eligibility missing or stale")
    stopped, committed = [], False
    with (state_dir / "finalizer.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        driver, children = _discover(setting); pids = [row["pid"] for row in children]
        try:
            for pid in pids:
                os.kill(pid, signal.SIGSTOP); stopped.append(pid)
            _wait_stopped(pids)
            paths = list(chain_paths(setting)); sizes = [path.stat().st_size for path in paths]; time.sleep(2)
            if sizes != [path.stat().st_size for path in paths]:
                raise RuntimeError("WP7 chain sizes changed while paused")
            diagnostics = collect(setting, paths); gates = policy_gates(diagnostics, policy)
            if not all(gates.values()):
                raise RuntimeError("paused WP7 snapshot failed gates")
            audit = {
                "schema_version": "wp7-fs7-final-stop-audit-v1",
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "status": "COMMIT_TO_EXTERNAL_STOP", "setting": setting,
                "policy_sha256": sha(POLICY), "activation_sha256": sha(ACTIVATION),
                "eligibility_sha256": sha(eligibility), "driver": driver, "children": children,
                "stable_sizes": sizes, "final_diagnostics": diagnostics,
                "final_policy_gates": gates, "checkpoints_edited": False,
            }
            path = state_dir / "final_stop_audit.json"; atomic_write_json(path, audit); committed = True
            for pid in pids:
                os.kill(pid, signal.SIGTERM)
            for pid in pids:
                if _alive(pid): os.kill(pid, signal.SIGCONT)
            remaining = _wait_exit(pids, 20); escalated = list(remaining)
            for pid in remaining:
                os.kill(pid, signal.SIGKILL)
            remaining = _wait_exit(remaining, 5)
            post = collect(setting, paths); post_gates = policy_gates(post, policy)
            audit.update({
                "completed_at_utc": datetime.now(timezone.utc).isoformat(),
                "status": "EXTERNALLY_STOPPED" if not remaining else "EXTERNALLY_STOPPED_WITH_EXIT_WARNING",
                "children_requiring_sigkill": escalated, "children_still_alive_after_sigkill": remaining,
                "post_termination_diagnostics": post, "post_termination_policy_gates": post_gates,
                "post_termination_gates_pass": all(post_gates.values()),
            })
            atomic_write_json(path, audit); return audit
        except Exception as exc:
            if not committed:
                for pid in stopped:
                    if _alive(pid): os.kill(pid, signal.SIGCONT)
                atomic_write_json(state_dir / "final_stop_audit.json", {"status": "ABORTED_RESUMED", "setting": setting, "error": f"{type(exc).__name__}: {exc}", "checkpoints_edited": False})
            raise


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(); parser.add_argument("setting", choices=SETTINGS); args = parser.parse_args()
    print(json.dumps({"setting": args.setting, "status": finalize(args.setting)["status"]}, sort_keys=True))
