#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PYTHONPATH=. .venv/bin/python tools/package_results.py
echo "Copy WP4_F1_WSL2_RESULTS.tar.gz and its .sha256 file back to the Mac."
