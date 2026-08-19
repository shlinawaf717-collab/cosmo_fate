#!/usr/bin/env bash
set -euo pipefail
ROOT="${WP4_F1_ROOT:-$HOME/WP4_F1_WSL2_TASKPACK_20260813}"
cd "$ROOT"
.venv/bin/python - <<'PY'
import hashlib,json
from datetime import datetime,timezone
from pathlib import Path
root=Path.cwd(); pre=root/'work/f1_nested/nested_preflight.json'; plan=root/'work/f1_nested/run_plan.json'; act=root/'work/f1_nested/activation.json'
p=json.loads(pre.read_text()); assert p['status']=='PASS'
def sha(x): return hashlib.sha256(x.read_bytes()).hexdigest()
out=root/'work/f1_nested/NESTED_PRODUCTION_STARTED.json'
if not out.exists():
    out.write_text(json.dumps({'schema_version':'wp4-f1-nested-start-v1',
        'created_at_utc':datetime.now(timezone.utc).isoformat(),
        'production_authorized':True,'preflight_sha256':sha(pre),
        'plan_sha256':sha(plan),'activation_sha256':sha(act)},indent=2,sort_keys=True)+'\n')
print('nested production authorized')
PY
if pgrep -f 'pipeline/run_wp4_f1_nested.py' >/dev/null; then
  echo 'Nested driver already running; no duplicate started.'
else
  tmux new-session -d -s wp4-f1-nested "cd '$ROOT' && export PYTHONPATH=. && exec .venv/bin/python pipeline/run_wp4_f1_nested.py --output-root '$ROOT/work/f1_nested' >> '$ROOT/work/f1_nested/driver_launcher.log' 2>&1"
fi
sleep 3
bash nested_increment_20260819/wsl/12_status.sh
