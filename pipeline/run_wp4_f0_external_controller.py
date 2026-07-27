#!/usr/bin/env python3
"""Run the authoritative WP4 F0 evaluator and eligible-stop finalizer."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from pipeline.evaluate_wp4_f0_external_stop import (
    DEFAULT_ACTIVATION,
    DEFAULT_STATE_DIR,
    evaluate_once,
)


def _append_event(path: Path, event: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(event)
    payload["timestamp_utc"] = datetime.now(timezone.utc).isoformat()
    line = json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    try:
        os.write(descriptor, line.encode("utf-8"))
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def run_controller(
    activation: Path,
    state_dir: Path,
    interval_seconds: float,
) -> int:
    events = state_dir / "controller_events.jsonl"
    _append_event(events, {"event": "controller_start", "pid": os.getpid()})
    while True:
        payload = evaluate_once(activation, state_dir)
        _append_event(
            events,
            {
                "event": "evaluation",
                "status": payload["status"],
                "snapshot_sha256": payload["snapshot_sha256"],
            },
        )
        if payload["stop_eligible"]:
            command = [
                sys.executable,
                str(
                    Path(__file__).resolve().with_name(
                        "finalize_wp4_f0_external_stop.py"
                    )
                ),
                "--activation",
                str(activation),
                "--state-dir",
                str(state_dir),
                "--execute",
            ]
            completed = subprocess.run(command, check=False, capture_output=True, text=True)
            _append_event(
                events,
                {
                    "event": "finalizer_exit",
                    "returncode": completed.returncode,
                    "stdout": completed.stdout.strip(),
                    "stderr": completed.stderr.strip(),
                },
            )
            return completed.returncode
        time.sleep(interval_seconds)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--activation", type=Path, default=DEFAULT_ACTIVATION)
    parser.add_argument("--state-dir", type=Path, default=DEFAULT_STATE_DIR)
    parser.add_argument("--interval-seconds", type=float, default=1800.0)
    args = parser.parse_args()
    return run_controller(args.activation, args.state_dir, args.interval_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
