#!/usr/bin/env bash
set -euo pipefail
ROOT="${WP4_F1_ROOT:-$HOME/WP4_F1_WSL2_TASKPACK_20260813}"
EXT="$ROOT/nested_increment_20260819"
cd "$ROOT"
mkdir -p "$EXT/logs" work/f1_nested work/nested_packages pipeline
exec > >(tee -a "$EXT/logs/install_preflight.log") 2>&1

echo '[1/9] Increment and original task-package integrity'
python3 "$EXT/pipeline/verify_nested_increment.py" --root "$EXT"
python3 tools/verify_package_manifest.py --root "$ROOT" --manifest PACKAGE_MANIFEST.json --output work/f1_nested/original_package_integrity.json
.venv/bin/python tools/verify_input_manifest.py --root payload --manifest payload/runs/prd_extension/wp4_full_cmb/input_manifest.json --output work/f1_nested/input_integrity.json

echo '[2/9] Closed F1 MCMC precondition'
.venv/bin/python - <<'PY'
import json
p=json.load(open('work/f1/external_monitor/final_stop_audit.json'))
assert p['post_termination_gates_pass'] is True
assert p['status'] in ('EXTERNALLY_STOPPED','EXTERNALLY_STOPPED_WITH_EXIT_WARNING')
print('F1 closure PASS')
PY

echo '[3/9] Install MPI toolchain'
sudo apt-get update
sudo apt-get install -y openmpi-bin libopenmpi-dev gfortran make
export PATH="$HOME/.local/bin:$PATH"
uv pip install --python .venv/bin/python 'mpi4py==4.1.0'

echo '[4/9] Install isolated PolyChordLite 1.20.1'
.venv/bin/cobaya-install polychord -p "$ROOT/work/nested_packages" --no-set-global --no-progress-bars
.venv/bin/cobaya-install polychord -p "$ROOT/work/nested_packages" --no-set-global --test --no-progress-bars

echo '[5/9] Install exact frozen runtime scripts'
cp "$EXT"/pipeline/prepare_wp4_f1_nested.py "$ROOT/pipeline/prepare_wp4_f1_nested.py"
cp "$EXT"/pipeline/run_wp4_f1_nested.py "$ROOT/pipeline/run_wp4_f1_nested.py"
cp "$EXT"/pipeline/report_wp4_f1_nested.py "$ROOT/pipeline/report_wp4_f1_nested.py"
cp "$EXT"/pipeline/fate.py "$ROOT/pipeline/fate.py"

echo '[6/9] Materialize and hash 12 WSL2 configs'
PYTHONPATH=. .venv/bin/python pipeline/prepare_wp4_f1_nested.py \
  --project-root "$ROOT" --base-config "$ROOT/payload/pipeline/wp4_f1.yaml" \
  --packages-path "$ROOT/payload/data/cobaya_packages" \
  --polychord-path "$ROOT/work/nested_packages/code/PolyChordLite" \
  --output-root "$ROOT/work/f1_nested" --platform-role wsl2_production

echo '[7/9] MPI/PolyChord no-sampling smoke'
.venv/bin/python - <<'PY'
from pathlib import Path
import yaml
root=Path.cwd(); source=root/'work/f1_nested/configs/seed2026082001_cpl.yaml'
info=yaml.safe_load(source.read_text()); info['output']=str((root/'work/f1_nested/smoke/chain').resolve())
target=root/'work/f1_nested/smoke.yaml'; target.write_text(yaml.safe_dump(info,sort_keys=False,width=100))
PY
FIRST="$ROOT/work/f1_nested/smoke.yaml"
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
  mpirun -np 2 .venv/bin/cobaya-run "$FIRST" --test > "$ROOT/work/f1_nested/mpi_smoke.log" 2>&1
grep -q 'Test initialization successful' "$ROOT/work/f1_nested/mpi_smoke.log"

echo '[8/9] Bounded timing pilot (diagnostic only; never an endpoint)'
.venv/bin/python - <<'PY'
from pathlib import Path
import yaml
root=Path.cwd(); source=root/'work/f1_nested/configs/seed2026082001_cpl.yaml'
info=yaml.safe_load(source.read_text()); pc=info['sampler']['polychord']
pc.update({'nlive':36,'num_repeats':'1d','nprior':'2nlive','nfail':'nlive',
           'do_clustering':False,'precision_criterion':0.5,'max_ndead':20,
           'seed':2026082099,'read_resume':False,'write_resume':True})
info['output']=str((root/'work/f1_nested/pilot/chain').resolve())
target=root/'work/f1_nested/pilot.yaml'; target.write_text(yaml.safe_dump(info,sort_keys=False,width=100))
PY
PILOT_START=$(date +%s)
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
  mpirun -np 4 .venv/bin/cobaya-run "$ROOT/work/f1_nested/pilot.yaml" --force \
  > "$ROOT/work/f1_nested/pilot.log" 2>&1
PILOT_SECONDS=$(($(date +%s)-PILOT_START))
printf '%s\n' "$PILOT_SECONDS" > "$ROOT/work/f1_nested/pilot_runtime_seconds.txt"
echo "pilot_runtime_seconds=$PILOT_SECONDS"

echo '[9/9] Freeze aggregate preflight'
.venv/bin/python - <<'PY'
import hashlib,json,platform
from datetime import datetime,timezone
from pathlib import Path
root=Path.cwd(); out=root/'work/f1_nested/nested_preflight.json'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
plan=root/'work/f1_nested/run_plan.json'; activation=root/'work/f1_nested/activation.json'
p={'schema_version':'wp4-f1-nested-preflight-v1','status':'PASS',
   'created_at_utc':datetime.now(timezone.utc).isoformat(),
   'platform':platform.platform(),'machine':platform.machine(),
   'plan_sha256':sha(plan),'activation_sha256':sha(activation),
   'polychord_test':'PASS','mpi_smoke':'PASS',
   'pilot_runtime_seconds':int((root/'work/f1_nested/pilot_runtime_seconds.txt').read_text()),
   'pilot_scientific_role':'diagnostic_only_excluded_from_all_endpoints',
   'nested_production_samples_exist':False}
out.write_text(json.dumps(p,indent=2,sort_keys=True)+'\n')
print(json.dumps(p))
PY
echo 'NESTED PRE-FLIGHT PASS. You may run windows\11_start_nested.cmd.'
