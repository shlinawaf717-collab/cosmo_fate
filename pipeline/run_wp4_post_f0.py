#!/usr/bin/env python3
"""Wait for audited F0 closure, then build the F1 proposal exactly once."""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

from pipeline.build_wp4_f1_proposal import (
    DEFAULT_AUDIT,
    DEFAULT_CLOSURE_AUDIT,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--poll-seconds", type=float, default=300.0)
    args = parser.parse_args()
    while True:
        if DEFAULT_AUDIT.is_file():
            return 0
        if DEFAULT_CLOSURE_AUDIT.is_file():
            command = [
                sys.executable,
                str(
                    Path(__file__).resolve().with_name(
                        "build_wp4_f1_proposal.py"
                    )
                ),
            ]
            completed = subprocess.run(command, check=False)
            if completed.returncode == 0:
                return 0
        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
