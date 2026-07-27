#!/usr/bin/env python3
"""Transactional finalizer for an eligible WP4 F0 external stop."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import signal
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from pipeline.evaluate_wp4_f0_external_stop import (
    DEFAULT_ACTIVATION,
    DEFAULT_STATE_DIR,
    POLICY_PATH,
    ROOT,
    policy_gates,
    sha256_file,
    validate_activation,
)
from pipeline.monitor_wp4_f0 import collect_diagnostics


SCHEMA_VERSION = "wp4-f0-external-stop-final-audit-v1"
DRIVER_LOCK = ROOT / "runs/prd_extension/wp4_full_cmb/f0/driver.lock"
RUN_PLAN = ROOT / "runs/prd_extension/wp4_full_cmb/f0/run_plan.json"
FINAL_AUDIT = DEFAULT_STATE_DIR / "final_stop_audit.json"
TRANSACTION_LOCK = DEFAULT_STATE_DIR / "finalizer.lock"


class ExternalStopError(RuntimeError):
    """Raised when the stop transaction cannot proceed safely."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
        temporary = Path(handle.name)
    os.replace(temporary, path)


def _process_table() -> list[dict]:
    completed = subprocess.run(
        ["ps", "-axo", "pid=,ppid=,state=,command="],
        check=True,
        capture_output=True,
        text=True,
    )
    rows = []
    for line in completed.stdout.splitlines():
        fields = line.strip().split(None, 3)
        if len(fields) < 4:
            continue
        rows.append(
            {
                "pid": int(fields[0]),
                "ppid": int(fields[1]),
                "state": fields[2],
                "command": fields[3],
            }
        )
    return rows


def discover_f0_processes() -> tuple[dict, list[dict]]:
    if not DRIVER_LOCK.is_file():
        raise ExternalStopError("F0 driver lock is missing")
    driver_pid = int(DRIVER_LOCK.read_text(encoding="utf-8").strip())
    table = _process_table()
    by_pid = {row["pid"]: row for row in table}
    driver = by_pid.get(driver_pid)
    if driver is None:
        raise ExternalStopError(f"F0 driver PID {driver_pid} is not alive")
    if "pipeline/run_wp4_f0.py --jobs 4" not in driver["command"]:
        raise ExternalStopError("driver command does not match frozen F0 command")
    direct_children = [row for row in table if row["ppid"] == driver_pid]
    cobaya_children = [
        row
        for row in direct_children
        if "cobaya-run" in row["command"] and "--no-mpi" in row["command"]
    ]
    if len(cobaya_children) != 4:
        raise ExternalStopError(
            f"expected four direct Cobaya children, found {len(cobaya_children)}"
        )
    for ordinal in range(1, 5):
        marker = f"wp4_full_cmb/f0/c{ordinal}/run.yaml"
        matches = [row for row in cobaya_children if marker in row["command"]]
        if len(matches) != 1:
            raise ExternalStopError(f"child mapping failed for c{ordinal}")
    return driver, sorted(cobaya_children, key=lambda row: row["command"])


def validate_runtime_hashes(activation: dict) -> dict:
    records = {}
    for name, registered in activation["runtime_hashes"].items():
        path = Path(registered["path"])
        if not path.is_absolute():
            path = ROOT / path
        actual = sha256_file(path)
        if actual != registered["sha256"]:
            raise ExternalStopError(f"runtime hash mismatch: {name}")
        records[name] = {"path": str(path), "sha256": actual}
    plan = _load_json(RUN_PLAN)
    for chain in plan["chains"]:
        run_yaml = ROOT / chain["run_yaml"]
        if sha256_file(run_yaml) != chain["run_yaml_sha256"]:
            raise ExternalStopError(
                f"run YAML no longer matches plan: {run_yaml}"
            )
    return records


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


def _state(pid: int) -> str | None:
    completed = subprocess.run(
        ["ps", "-o", "state=", "-p", str(pid)],
        check=False,
        capture_output=True,
        text=True,
    )
    value = completed.stdout.strip()
    return value or None


def _wait_for_stopped(pids: list[int], timeout: float = 10.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if all((_state(pid) or "").startswith("T") for pid in pids):
            return
        time.sleep(0.1)
    raise ExternalStopError("Cobaya children did not all enter stopped state")


def _wait_for_exit(pids: list[int], timeout: float) -> list[int]:
    deadline = time.monotonic() + timeout
    remaining = list(pids)
    while time.monotonic() < deadline:
        remaining = [pid for pid in remaining if _alive(pid)]
        if not remaining:
            return []
        time.sleep(0.2)
    return remaining


def _resume_alive(pids: list[int]) -> None:
    for pid in pids:
        if _alive(pid):
            os.kill(pid, signal.SIGCONT)


def _chain_sizes(policy: dict) -> list[int]:
    return [(ROOT / path).stat().st_size for path in policy["chains"]]


def _final_diagnostics(policy: dict) -> dict:
    burns = [
        policy["statistics"]["rminus1"]["primary_row_burn_fraction"],
        *policy["statistics"]["rminus1"]["sensitivity_row_burn_fractions"],
    ]
    return collect_diagnostics(
        [ROOT / path for path in policy["chains"]],
        burn_fractions=burns,
        primary_burn=policy["statistics"]["ess"]["row_burn_fraction"],
    )


def finalize(
    activation_path: Path = DEFAULT_ACTIVATION,
    state_dir: Path = DEFAULT_STATE_DIR,
    execute: bool = False,
) -> dict:
    policy = _load_json(POLICY_PATH)
    activation = validate_activation(activation_path, policy)
    for component in ("finalizer", "controller"):
        registered = activation["hashes"][component]
        component_path = Path(registered["path"])
        if sha256_file(component_path) != registered["sha256"]:
            raise ExternalStopError(f"{component} hash mismatch")
    eligibility_path = state_dir / "stop_eligible.json"
    if not eligibility_path.is_file():
        raise ExternalStopError("no authoritative stop eligibility artifact")
    eligibility = _load_json(eligibility_path)
    if eligibility["policy_sha256"] != sha256_file(POLICY_PATH):
        raise ExternalStopError("eligibility policy hash mismatch")
    if (
        eligibility["statistics_sha256"]
        != policy["implementation"]["statistics_sha256"]
    ):
        raise ExternalStopError("eligibility statistics hash mismatch")

    state_dir.mkdir(parents=True, exist_ok=True)
    stopped_pids: list[int] = []
    committed_to_termination = False
    with TRANSACTION_LOCK.open("w", encoding="utf-8") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ExternalStopError("another finalizer holds the lock") from exc
        driver, children = discover_f0_processes()
        runtime_hashes = validate_runtime_hashes(activation)
        child_pids = [child["pid"] for child in children]
        pre_sizes = _chain_sizes(policy)
        try:
            for pid in child_pids:
                os.kill(pid, signal.SIGSTOP)
                stopped_pids.append(pid)
            _wait_for_stopped(child_pids)
            stable_first = _chain_sizes(policy)
            time.sleep(2.0)
            stable_second = _chain_sizes(policy)
            if stable_first != stable_second:
                raise ExternalStopError("chain sizes changed while children paused")
            diagnostics = _final_diagnostics(policy)
            gates = policy_gates(diagnostics, policy)
            if not all(gates.values()):
                raise ExternalStopError("final paused snapshot failed a policy gate")
            audit = {
                "schema_version": SCHEMA_VERSION,
                "created_at_utc": _utc_now(),
                "status": "DRY_RUN_RESUMED" if not execute else "COMMIT_TO_EXTERNAL_STOP",
                "execute": execute,
                "activation_path": str(activation_path),
                "activation_sha256": sha256_file(activation_path),
                "eligibility_path": str(eligibility_path),
                "eligibility_sha256": sha256_file(eligibility_path),
                "policy_sha256": sha256_file(POLICY_PATH),
                "statistics_sha256": policy["implementation"][
                    "statistics_sha256"
                ],
                "runtime_hashes": runtime_hashes,
                "driver": driver,
                "children": children,
                "chain_sizes_before_pause": pre_sizes,
                "chain_sizes_stable_while_paused": stable_second,
                "final_diagnostics": diagnostics,
                "final_policy_gates": gates,
                "cobaya_checkpoints_edited": False,
            }
            audit_path = state_dir / "final_stop_audit.json"
            _atomic_json(audit_path, audit)
            if not execute:
                _resume_alive(stopped_pids)
                return audit

            committed_to_termination = True
            # Queue TERM while stopped, then CONT so it can be delivered.
            for pid in child_pids:
                os.kill(pid, signal.SIGTERM)
            for pid in child_pids:
                if _alive(pid):
                    os.kill(pid, signal.SIGCONT)
            remaining = _wait_for_exit(child_pids, timeout=20.0)
            escalated = list(remaining)
            for pid in remaining:
                os.kill(pid, signal.SIGKILL)
            _wait_for_exit(remaining, timeout=5.0)
            driver_remaining = _wait_for_exit([driver["pid"]], timeout=30.0)
            post_diagnostics = _final_diagnostics(policy)
            post_gates = policy_gates(post_diagnostics, policy)
            audit.update(
                {
                    "completed_at_utc": _utc_now(),
                    "status": (
                        "EXTERNALLY_STOPPED"
                        if not escalated and not driver_remaining
                        else "EXTERNALLY_STOPPED_WITH_EXIT_WARNING"
                    ),
                    "children_requiring_sigkill": escalated,
                    "driver_still_alive_after_timeout": driver_remaining,
                    "post_termination_diagnostics": post_diagnostics,
                    "post_termination_policy_gates": post_gates,
                    "post_termination_gates_pass": all(post_gates.values()),
                }
            )
            _atomic_json(audit_path, audit)
            return audit
        except Exception as exc:
            if not committed_to_termination:
                _resume_alive(stopped_pids)
                aborted = {
                    "schema_version": SCHEMA_VERSION,
                    "created_at_utc": _utc_now(),
                    "status": "ABORTED_RESUMED",
                    "error": f"{type(exc).__name__}: {exc}",
                    "paused_children": stopped_pids,
                    "resumed_alive_children": [
                        pid for pid in stopped_pids if _alive(pid)
                    ],
                    "cobaya_checkpoints_edited": False,
                }
                _atomic_json(state_dir / "final_stop_audit.json", aborted)
            raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--activation", type=Path, default=DEFAULT_ACTIVATION)
    parser.add_argument("--state-dir", type=Path, default=DEFAULT_STATE_DIR)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="actually terminate after the paused final audit; otherwise resume",
    )
    args = parser.parse_args()
    audit = finalize(args.activation, args.state_dir, execute=args.execute)
    print(json.dumps({"status": audit["status"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
