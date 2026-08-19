#!/usr/bin/env bash
set -u
ROOT="${WP4_F1_ROOT:-$HOME/WP4_F1_WSL2_TASKPACK_20260813}"
cd "$ROOT"
echo '=== process health ==='
tmux ls 2>/dev/null | grep wp4-f1-nested || true
ps -eo pid,ppid,state,%cpu,%mem,etime,cmd | grep -E 'run_wp4_f1_nested|mpirun.*f1_nested|cobaya-run.*f1_nested' | grep -v grep || true
echo '=== blinded completion state ==='
.venv/bin/python - <<'PY'
import json
from pathlib import Path
p=Path('work/f1_nested/completion.json')
if p.exists():
    x=json.loads(p.read_text()); print({'status':x.get('status'),'completed_runs':x.get('completed_runs',0),'total_runs':12})
else:
    print({'status':'NOT_STARTED','completed_runs':0,'total_runs':12})
for seed in (2026082001,2026082002,2026082003):
    for model in ('cpl','lcdm','rip','decay'):
        root=Path(f'work/f1_nested/seed{seed}/{model}')
        resumes=list(root.glob('chain_polychord_raw/*.resume'))+list(root.glob('*.resume'))
        evidence=(root/'chain.evidence.yaml').exists()
        print(seed,model,'resume_files',len(resumes),'complete',evidence)
PY
echo 'No logZ, posterior, or fate endpoint is shown during production.'
