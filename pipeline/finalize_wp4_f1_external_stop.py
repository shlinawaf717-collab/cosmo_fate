#!/usr/bin/env python3
"""Transactional finalizer for an eligible WP4 F1 external stop."""

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

from pipeline.evaluate_wp4_f1_external_stop import (
    DEFAULT_ACTIVATION, DEFAULT_STATE_DIR, POLICY_PATH, ROOT,
    policy_gates, sha256_file, validate_activation,
)
from pipeline.monitor_wp4_f1 import collect_diagnostics


DRIVER_LOCK = ROOT / "runs/prd_extension/wp4_full_cmb/f1/driver.lock"
RUN_PLAN = ROOT / "runs/prd_extension/wp4_full_cmb/f1/run_plan.json"
TRANSACTION_LOCK = DEFAULT_STATE_DIR / "finalizer.lock"


class ExternalStopError(RuntimeError):
    """Raised when the F1 stop transaction cannot proceed safely."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
        temporary = Path(handle.name)
    os.replace(temporary, path)


def _process_table() -> list[dict]:
    completed = subprocess.run(
        ["ps", "-axo", "pid=,ppid=,state=,command="], check=True,
        capture_output=True, text=True,
    )
    rows = []
    for line in completed.stdout.splitlines():
        fields = line.strip().split(None, 3)
        if len(fields) == 4:
            rows.append({"pid": int(fields[0]), "ppid": int(fields[1]), "state": fields[2], "command": fields[3]})
    return rows


def discover_f1_processes() -> tuple[dict, list[dict]]:
    if not DRIVER_LOCK.is_file():
        raise ExternalStopError("F1 driver lock is missing")
    driver_pid = int(DRIVER_LOCK.read_text(encoding="utf-8").strip())
    table = _process_table()
    driver = {row["pid"]: row for row in table}.get(driver_pid)
    if driver is None or "pipeline/run_wp4_f1.py --jobs 4" not in driver["command"]:
        raise ExternalStopError("live driver does not match the frozen F1 command")
    children = [
        row for row in table
        if row["ppid"] == driver_pid and "cobaya-run" in row["command"] and "--no-mpi" in row["command"]
    ]
    if len(children) != 4:
        raise ExternalStopError(f"expected four direct Cobaya children, found {len(children)}")
    for ordinal in range(1, 5):
        marker = f"wp4_full_cmb/f1/c{ordinal}/run.yaml"
        if sum(marker in row["command"] for row in children) != 1:
            raise ExternalStopError(f"child mapping failed for c{ordinal}")
    return driver, sorted(children, key=lambda row: row["command"])


def validate_runtime_hashes(activation: dict) -> dict:
    records = {}
    for name, registered in activation["runtime_hashes"].items():
        path = ROOT / registered["path"]
        actual = sha256_file(path)
        if actual != registered["sha256"]:
            raise ExternalStopError(f"runtime hash mismatch: {name}")
        records[name] = {"path": str(path), "sha256": actual}
    plan = _load_json(RUN_PLAN)
    for chain in plan["chains"]:
        path = ROOT / chain["run_yaml"]
        if sha256_file(path) != chain["run_yaml_sha256"]:
            raise ExternalStopError(f"run YAML no longer matches plan: {path}")
    return records


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False


def _state(pid: int) -> str:
    completed = subprocess.run(["ps", "-o", "state=", "-p", str(pid)], capture_output=True, text=True, check=False)
    return completed.stdout.strip()


def _wait_stopped(pids: list[int], timeout: float = 10.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if all(_state(pid).startswith("T") for pid in pids):
            return
        time.sleep(0.1)
    raise ExternalStopError("Cobaya children did not all stop")


def _wait_exit(pids: list[int], timeout: float) -> list[int]:
    deadline = time.monotonic() + timeout
    remaining = list(pids)
    while time.monotonic() < deadline:
        remaining = [pid for pid in remaining if _alive(pid)]
        if not remaining:
            break
        time.sleep(0.2)
    return remaining


def _resume(pids: list[int]) -> None:
    for pid in pids:
        if _alive(pid):
            os.kill(pid, signal.SIGCONT)


def _diagnostics(policy: dict) -> dict:
    r = policy["statistics"]["rminus1"]
    return collect_diagnostics(
        [ROOT / path for path in policy["chains"]],
        [r["primary_row_burn_fraction"], *r["sensitivity_row_burn_fractions"]],
        policy["statistics"]["ess"]["row_burn_fraction"],
    )


def finalize(activation_path: Path = DEFAULT_ACTIVATION, state_dir: Path = DEFAULT_STATE_DIR, execute: bool = False) -> dict:
    policy = _load_json(POLICY_PATH)
    activation = validate_activation(activation_path, policy)
    for component in ("finalizer", "controller"):
        registered = activation["hashes"][component]
        if sha256_file(ROOT / registered["path"]) != registered["sha256"]:
            raise ExternalStopError(f"{component} hash mismatch")
    eligibility_path = state_dir / "stop_eligible.json"
    if not eligibility_path.is_file():
        raise ExternalStopError("no authoritative F1 stop eligibility artifact")
    eligibility = _load_json(eligibility_path)
    if eligibility["policy_sha256"] != sha256_file(POLICY_PATH):
        raise ExternalStopError("eligibility policy hash mismatch")
    state_dir.mkdir(parents=True, exist_ok=True)
    stopped: list[int] = []
    committed = False
    with TRANSACTION_LOCK.open("w", encoding="utf-8") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ExternalStopError("another F1 finalizer holds the lock") from exc
        driver, children = discover_f1_processes()
        runtime_hashes = validate_runtime_hashes(activation)
        pids = [row["pid"] for row in children]
        try:
            for pid in pids:
                os.kill(pid, signal.SIGSTOP)
                stopped.append(pid)
            _wait_stopped(pids)
            paths = [ROOT / path for path in policy["chains"]]
            sizes_first = [path.stat().st_size for path in paths]
            time.sleep(2.0)
            sizes_second = [path.stat().st_size for path in paths]
            if sizes_first != sizes_second:
                raise ExternalStopError("F1 chain sizes changed while paused")
            diagnostics = _diagnostics(policy)
            gates = policy_gates(diagnostics, policy)
            if not all(gates.values()):
                raise ExternalStopError("final paused F1 snapshot failed a gate")
            audit = {
                "schema_version": "wp4-f1-external-stop-final-audit-v1",
                "created_at_utc": _utc_now(), "execute": execute,
                "status": "DRY_RUN_RESUMED" if not execute else "COMMIT_TO_EXTERNAL_STOP",
                "activation_sha256": sha256_file(activation_path),
                "eligibility_sha256": sha256_file(eligibility_path),
                "policy_sha256": sha256_file(POLICY_PATH),
                "runtime_hashes": runtime_hashes, "driver": driver, "children": children,
                "stable_chain_sizes": sizes_second, "final_diagnostics": diagnostics,
                "final_policy_gates": gates, "cobaya_checkpoints_edited": False,
            }
            audit_path = state_dir / "final_stop_audit.json"
            _atomic_json(audit_path, audit)
            if not execute:
                _resume(stopped)
                return audit
            committed = True
            for pid in pids:
                os.kill(pid, signal.SIGTERM)
            _resume(pids)
            remaining = _wait_exit(pids, 20.0)
            for pid in remaining:
                os.kill(pid, signal.SIGKILL)
            _wait_exit(remaining, 5.0)
            driver_remaining = _wait_exit([driver["pid"]], 30.0)
            post = _diagnostics(policy)
            post_gates = policy_gates(post, policy)
            audit.update({
                "completed_at_utc": _utc_now(),
                "status": "EXTERNALLY_STOPPED" if not remaining and not driver_remaining else "EXTERNALLY_STOPPED_WITH_EXIT_WARNING",
                "children_requiring_sigkill": remaining,
                "driver_still_alive_after_timeout": driver_remaining,
                "post_termination_diagnostics": post,
                "post_termination_policy_gates": post_gates,
                "post_termination_gates_pass": all(post_gates.values()),
            })
            _atomic_json(audit_path, audit)
            return audit
        except Exception as exc:
            if not committed:
                _resume(stopped)
                _atomic_json(state_dir / "final_stop_audit.json", {
                    "schema_version": "wp4-f1-external-stop-final-audit-v1",
                    "created_at_utc": _utc_now(), "status": "ABORTED_RESUMED",
                    "error": f"{type(exc).__name__}: {exc}", "paused_children": stopped,
                    "resumed_alive_children": [pid for pid in stopped if _alive(pid)],
                    "cobaya_checkpoints_edited": False,
                })
            raise


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    print(json.dumps({"status": finalize(execute=args.execute)["status"]}, sort_keys=True))
