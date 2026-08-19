#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
.venv/bin/python tools/aggregate_preflight.py --require-pass --output work/preflight/PREFLIGHT_GO.json
if find work/f1 -path '*/chain.*.txt' -type f -print -quit 2>/dev/null | grep -q .; then
  echo "Existing F1 samples found: safe resume will be used; no new chain set is created."
fi
if [ ! -f work/f1/external_stop_activation.json ]; then
  PYTHONPATH=. .venv/bin/python tools/prepare_wsl2_f1.py
fi
mkdir -p work/f1
PYTHONPATH=. .venv/bin/python tools/authorize_wsl2_production.py
if ! pgrep -f 'tools/run_wsl2_f1.py' >/dev/null; then
  tmux new-session -d -s wp4-f1-driver "cd '$ROOT' && export PYTHONPATH=. && exec .venv/bin/python tools/run_wsl2_f1.py >> work/f1/driver_launcher.log 2>&1"
else
  echo "F1 driver already running; not starting a duplicate."
fi
if ! pgrep -f 'tools/controller_wsl2_f1.py' >/dev/null; then
  tmux new-session -d -s wp4-f1-controller "cd '$ROOT' && export PYTHONPATH=. && exec .venv/bin/python tools/controller_wsl2_f1.py >> work/f1/controller_launcher.log 2>&1"
else
  echo "F1 controller already running; not starting a duplicate."
fi
sleep 5
bash wsl/06_status.sh
