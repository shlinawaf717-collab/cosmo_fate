#!/usr/bin/env bash
set -euo pipefail
ROOT="${WP4_F1_ROOT:-$HOME/WP4_F1_WSL2_TASKPACK_20260813}"
cd "$ROOT"
PYTHONPATH=. .venv/bin/python nested_increment_20260819/pipeline/package_wp4_f1_nested_results.py
echo 'Nested return archive and checksum are ready for Windows copy.'
