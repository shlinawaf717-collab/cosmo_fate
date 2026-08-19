#!/usr/bin/env bash
set -euo pipefail
ROOT="${WP4_F1_ROOT:-$HOME/WP4_F1_WSL2_TASKPACK_20260813}"
cd "$ROOT"
.venv/bin/python - <<'PY'
import hashlib,json
from datetime import datetime,timezone
from pathlib import Path
s=Path('runs/prd_extension/wp5_bin4/production_system')
pre=s/'preflight.json';plan=s/'run_plan.json';act=s/'activation.json'
p=json.loads(pre.read_text());assert p['status']=='PASS'
def h(x):return hashlib.sha256(x.read_bytes()).hexdigest()
out=s/'WP5_PRODUCTION_STARTED.json'
if not out.exists():
    out.write_text(json.dumps({'schema_version':'wp5-bin4-start-v1','created_at_utc':datetime.now(timezone.utc).isoformat(),'production_authorized':True,'preflight_sha256':h(pre),'run_plan_sha256':h(plan),'activation_sha256':h(act)},indent=2,sort_keys=True)+'\n')
print('WP5 production authorized')
PY
if ! pgrep -f 'pipeline/run_wp5_bin4.py' >/dev/null; then
  tmux new-session -d -s wp5-driver "cd '$ROOT' && export PYTHONPATH=. && exec .venv/bin/python pipeline/run_wp5_bin4.py >> runs/prd_extension/wp5_bin4/production_system/driver_launcher.log 2>&1"
fi
for tag in 0p005 0p01 0p02; do
  if ! pgrep -f "run_wp5_external_controller.py $tag" >/dev/null; then
    tmux new-session -d -s "wp5-$tag" "cd '$ROOT' && export PYTHONPATH=. && exec .venv/bin/python pipeline/run_wp5_external_controller.py '$tag' --interval-seconds 1800 >> runs/prd_extension/wp5_bin4/production_system/delta_$tag/controller_launcher.log 2>&1"
  fi
done
sleep 3
bash wp5_increment_20260819/wsl/22_status.sh
