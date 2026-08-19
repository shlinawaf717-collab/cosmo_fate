#!/usr/bin/env bash
set -euo pipefail
ROOT="${WP4_F1_ROOT:-$HOME/WP4_F1_WSL2_TASKPACK_20260813}"
EXT="$ROOT/wp5_increment_20260819"
cd "$ROOT"; mkdir -p "$EXT/logs" pipeline plan runs/prd_extension/wp5_bin4
exec > >(tee -a "$EXT/logs/preflight.log") 2>&1

python3 "$EXT/payload/tools/verify_wp5_increment.py" --root "$EXT"
python3 tools/verify_package_manifest.py --root "$ROOT" --manifest PACKAGE_MANIFEST.json --output work/wp5_original_package_integrity.json
.venv/bin/python tools/verify_input_manifest.py --root payload --manifest payload/runs/prd_extension/wp4_full_cmb/input_manifest.json --output work/wp5_input_integrity.json
cp -a "$EXT/payload/." "$ROOT/"
if [ ! -e "$ROOT/data" ]; then ln -s "$ROOT/payload/data" "$ROOT/data"; fi

PYTHONPATH=. .venv/bin/python pipeline/wp5_formal_theory_gate.py --output runs/prd_extension/wp5_bin4/formal_theory_gate.json
PYTHONPATH=. .venv/bin/python pipeline/build_wp5_bin4_configs.py
for tag in 0p005 0p01 0p02; do
  PYTHONPATH=. OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
    .venv/bin/python pipeline/wp5_fixed_point_probe.py \
    --config "runs/prd_extension/wp5_bin4/configs/wp5_bin4_delta_$tag.yaml" \
    --packages data/cobaya_packages \
    --output "runs/prd_extension/wp5_bin4/fixed_points/wsl2_$tag.json"
  PYTHONPATH=. .venv/bin/python pipeline/compare_wp5_fixed_points.py \
    --reference "runs/prd_extension/wp5_bin4/fixed_points/mac_$tag.json" \
    --candidate "runs/prd_extension/wp5_bin4/fixed_points/wsl2_$tag.json" \
    --output "runs/prd_extension/wp5_bin4/fixed_points/comparison_$tag.json"
done
PYTHONPATH=. .venv/bin/python pipeline/run_wp5_bin4_smoke.py
PYTHONPATH=. .venv/bin/python pipeline/freeze_wp5_system.py
PYTHONPATH=. .venv/bin/python pipeline/run_wp5_system_smoke.py
PYTHONPATH=. .venv/bin/python pipeline/freeze_wp5_system.py

.venv/bin/python - <<'PY'
import hashlib,json,platform
from datetime import datetime,timezone
from pathlib import Path
r=Path.cwd();s=r/'runs/prd_extension/wp5_bin4/production_system';out=s/'preflight.json'
def h(p):return hashlib.sha256(p.read_bytes()).hexdigest()
smoke=json.loads((s/'system_smoke_audit.json').read_text());assert smoke['status']=='PASS'
fixed={}
for tag in ('0p005','0p01','0p02'):
    q=r/f'runs/prd_extension/wp5_bin4/fixed_points/comparison_{tag}.json'
    assert json.loads(q.read_text())['status']=='PASS';fixed[tag]=h(q)
p={'schema_version':'wp5-bin4-wsl2-preflight-v1','status':'PASS','created_at_utc':datetime.now(timezone.utc).isoformat(),'platform':platform.platform(),'plan_sha256':h(s/'run_plan.json'),'activation_sha256':h(s/'activation.json'),'system_smoke_sha256':h(s/'system_smoke_audit.json'),'fixed_point_comparison_sha256':fixed,'production_samples_exist':False}
out.write_text(json.dumps(p,indent=2,sort_keys=True)+'\n');print(json.dumps(p))
PY
echo 'WP5 PRE-FLIGHT PASS. Do not start concurrently with WP4 nested.'
