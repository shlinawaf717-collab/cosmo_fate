#!/usr/bin/env bash
set -u
ROOT="${WP4_F1_ROOT:-$HOME/WP4_F1_WSL2_TASKPACK_20260813}"
cd "$ROOT"
echo '=== processes ==='
tmux ls 2>/dev/null | grep wp5 || true
ps -eo pid,ppid,state,%cpu,%mem,etime,cmd | grep -E 'run_wp5_bin4|run_wp5_external_controller|cobaya-run.*production_system' | grep -v grep || true
echo '=== blinded width states ==='
.venv/bin/python - <<'PY'
import json
from pathlib import Path
base=Path('runs/prd_extension/wp5_bin4/production_system')
for tag in ('0p005','0p01','0p02'):
    rows=[]
    for i in range(1,5):
        p=base/f'delta_{tag}/c{i}/chain.1.txt'
        rows.append(sum(1 for line in p.open() if not line.startswith('#')) if p.exists() else 0)
    latest=base/f'delta_{tag}/external_monitor/latest.json'
    audit=base/f'delta_{tag}/external_monitor/final_stop_audit.json'
    state=json.loads(latest.read_text()).get('status') if latest.exists() else 'WAITING'
    final=json.loads(audit.read_text()).get('status') if audit.exists() else None
    print(tag,{'rows':rows,'controller':state,'final':final})
PY
