#!/usr/bin/env bash
set -euo pipefail
ROOT="${WP4_F1_ROOT:-$HOME/WP4_F1_WSL2_TASKPACK_20260813}"
cd "$ROOT"
PYTHONPATH=. .venv/bin/python wp5_increment_20260819/payload/tools/package_wp5_results.py
