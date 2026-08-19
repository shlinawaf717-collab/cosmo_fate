#!/usr/bin/env python3
"""Periodically evaluate WSL2 F1 and invoke its finalizer when eligible."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from tools.evaluate_wsl2_f1 import ROOT, STATE, evaluate


def append(event: dict) -> None:
    path = STATE / "controller_events.jsonl"; path.parent.mkdir(parents=True, exist_ok=True)
    payload = {**event, "timestamp_utc": datetime.now(timezone.utc).isoformat()}
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    try: os.write(fd, (json.dumps(payload, sort_keys=True) + "\n").encode()); os.fsync(fd)
    finally: os.close(fd)


def main() -> int:
    append({"event": "controller_start", "pid": os.getpid()})
    while True:
        try: payload = evaluate()
        except (FileNotFoundError, ValueError) as exc:
            append({"event": "chains_not_ready", "error": f"{type(exc).__name__}: {exc}"}); time.sleep(1800); continue
        append({"event": "evaluation", "status": payload["status"], "snapshot_sha256": payload["snapshot_sha256"]})
        if payload["stop_eligible"]:
            result = subprocess.run([sys.executable, str(ROOT / "tools/finalize_wsl2_f1.py")], capture_output=True, text=True)
            append({"event": "finalizer_exit", "returncode": result.returncode, "stdout": result.stdout.strip(), "stderr": result.stderr.strip()}); return result.returncode
        time.sleep(1800)


if __name__ == "__main__": raise SystemExit(main())
