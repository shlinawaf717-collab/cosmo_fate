#!/usr/bin/env python3
"""Periodically evaluate and finalize one blinded WP7 real-data setting."""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

from pipeline.evaluate_wp7_stop import SYSTEM, evaluate
from pipeline.monitor_wp7 import SETTINGS


def append(path, event):
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {**event, "timestamp_utc": datetime.now(timezone.utc).isoformat()}
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    try:
        os.write(descriptor, (json.dumps(payload, sort_keys=True) + "\n").encode()); os.fsync(descriptor)
    finally:
        os.close(descriptor)


def run(setting: str, interval: float) -> int:
    events = SYSTEM / setting / "external_monitor/controller_events.jsonl"
    append(events, {"event": "controller_start", "pid": os.getpid(), "setting": setting})
    while True:
        try:
            result = evaluate(setting)
        except (FileNotFoundError, ValueError) as exc:
            append(events, {"event": "chains_not_ready", "error": f"{type(exc).__name__}: {exc}"}); time.sleep(interval); continue
        append(events, {"event": "evaluation", "status": result["status"], "snapshot_sha256": result["snapshot_sha256"]})
        if result["stop_eligible"]:
            completed = subprocess.run([sys.executable, str(SYSTEM.parents[3] / "pipeline/finalize_wp7.py"), setting], capture_output=True, text=True)
            append(events, {"event": "finalizer_exit", "returncode": completed.returncode, "stdout": completed.stdout.strip(), "stderr": completed.stderr.strip()})
            return completed.returncode
        time.sleep(interval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("setting", choices=SETTINGS); parser.add_argument("--interval-seconds", type=float, default=1800); args = parser.parse_args()
    raise SystemExit(run(args.setting, args.interval_seconds))
