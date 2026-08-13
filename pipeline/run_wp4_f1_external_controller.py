#!/usr/bin/env python3
"""Run F1 authoritative evaluations and the eligible-stop finalizer."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from pipeline.evaluate_wp4_f1_external_stop import DEFAULT_ACTIVATION, DEFAULT_STATE_DIR, evaluate_once


def _append(path: Path, event: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {**event, "timestamp_utc": datetime.now(timezone.utc).isoformat()}
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    try:
        os.write(descriptor, (json.dumps(payload, sort_keys=True) + "\n").encode())
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def run_controller(activation: Path, state_dir: Path, interval_seconds: float) -> int:
    events = state_dir / "controller_events.jsonl"
    _append(events, {"event": "controller_start", "pid": os.getpid()})
    while True:
        try:
            payload = evaluate_once(activation, state_dir)
        except (FileNotFoundError, ValueError) as exc:
            _append(events, {"event": "chains_not_ready", "error": f"{type(exc).__name__}: {exc}"})
            time.sleep(interval_seconds)
            continue
        _append(events, {"event": "evaluation", "status": payload["status"], "snapshot_sha256": payload["snapshot_sha256"]})
        if payload["stop_eligible"]:
            completed = subprocess.run(
                [sys.executable, str(Path(__file__).with_name("finalize_wp4_f1_external_stop.py")), "--execute"],
                check=False, capture_output=True, text=True,
            )
            _append(events, {"event": "finalizer_exit", "returncode": completed.returncode, "stdout": completed.stdout.strip(), "stderr": completed.stderr.strip()})
            return completed.returncode
        time.sleep(interval_seconds)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interval-seconds", type=float, default=1800.0)
    args = parser.parse_args()
    raise SystemExit(run_controller(DEFAULT_ACTIVATION, DEFAULT_STATE_DIR, args.interval_seconds))
