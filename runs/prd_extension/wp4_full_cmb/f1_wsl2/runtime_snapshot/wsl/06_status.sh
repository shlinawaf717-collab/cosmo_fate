#!/usr/bin/env bash
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
echo "=== processes ==="
tmux ls 2>/dev/null || true
ps -eo pid,ppid,state,%cpu,%mem,etime,cmd | grep -E 'run_wsl2_f1|controller_wsl2_f1|cobaya-run.*/work/f1/c[1-4]/run.yaml' | grep -v grep || true
echo "=== chain rows ==="
for i in 1 2 3 4; do
  f="work/f1/c${i}/chain.1.txt"; rows=0
  [ -f "$f" ] && rows=$(awk 'BEGIN{n=0}!/^#/{n++}END{print n}' "$f")
  printf 'c%s rows=%s\n' "$i" "$rows"
  [ -f "work/f1/c${i}/run.log" ] && tail -n 1 "work/f1/c${i}/run.log"
done
echo "=== controller ==="
[ -f work/f1/external_monitor/latest.json ] && .venv/bin/python - <<'PY'
import json
p=json.load(open('work/f1/external_monitor/latest.json'))
print(json.dumps({'status':p['status'],'rows':[x['rows'] for x in p['chain_snapshots']],'rminus1':p['rminus1']['by_burn_fraction'],'gates':p['policy_gates']},indent=2))
PY
tail -n 5 work/f1/external_monitor/controller_events.jsonl 2>/dev/null || true
