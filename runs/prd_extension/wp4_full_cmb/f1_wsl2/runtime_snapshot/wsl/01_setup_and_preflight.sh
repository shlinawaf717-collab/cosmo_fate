#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
mkdir -p work/preflight logs
exec > >(tee -a logs/setup_preflight.log) 2>&1

echo "[1/8] Platform gate"
python3 tools/platform_gate.py --output work/preflight/platform.json

echo "[2/8] Package integrity"
python3 tools/verify_package_manifest.py --root "$ROOT" --manifest "$ROOT/PACKAGE_MANIFEST.json" --output work/preflight/package_integrity.json

echo "[3/8] Creating Python 3.13 environment"
sudo apt-get update
sudo apt-get install -y curl ca-certificates build-essential gfortran python3-dev tmux
if ! command -v uv >/dev/null 2>&1; then curl -LsSf https://astral.sh/uv/install.sh | sh; export PATH="$HOME/.local/bin:$PATH"; fi
export PATH="$HOME/.local/bin:$PATH"
uv python install 3.13.13
uv venv --python 3.13.13 .venv
uv pip install --python .venv/bin/python -r requirements.lock
.venv/bin/python tools/environment_report.py --output work/preflight/environment.json

echo "[4/8] Registered likelihood inputs"
.venv/bin/python tools/verify_input_manifest.py --root payload --manifest payload/runs/prd_extension/wp4_full_cmb/input_manifest.json --output work/preflight/input_integrity.json

echo "[5/8] CAMB geometry/spectrum drift screen"
PYTHONPATH=payload OMP_NUM_THREADS=1 .venv/bin/python payload/pipeline/camb_fixed_point_probe.py \
  --chain payload/runs/gate1/official/chain.1.txt --chain payload/runs/gate1/official/chain.2.txt \
  --chain payload/runs/gate1/official/chain.3.txt --chain payload/runs/gate1/official/chain.4.txt \
  --json work/preflight/wsl2_camb166.json --spectra-npz work/preflight/wsl2_camb166_spectra.npz
PYTHONPATH=payload .venv/bin/python payload/pipeline/compare_camb_fixed_point_probes.py \
  --reference-json reference/mac_camb166.json --candidate-json work/preflight/wsl2_camb166.json \
  --reference-npz reference/mac_camb166_spectra.npz --candidate-npz work/preflight/wsl2_camb166_spectra.npz \
  --output work/preflight/camb_comparison.json

echo "[6/8] Full F1 fixed-point likelihood drift screen"
PYTHONPATH=payload OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
  .venv/bin/python tools/f1_fixed_point_probe.py --config payload/pipeline/wp4_f1.yaml \
  --packages payload/data/cobaya_packages --output work/preflight/wsl2_f1_fixed_point.json
.venv/bin/python tools/compare_f1_fixed_point.py --reference reference/mac_f1_fixed_point.json \
  --candidate work/preflight/wsl2_f1_fixed_point.json --output work/preflight/f1_fixed_point_comparison.json

echo "[7/8] No-sampling F1 smoke"
PYTHONPATH=payload .venv/bin/python tools/run_wsl2_smoke.py --output work/preflight/f1_smoke_test.json

echo "[8/8] Aggregate gate"
PYTHONPATH=. .venv/bin/python tools/prepare_wsl2_f1.py
.venv/bin/python tools/verify_wsl2_activation.py --output work/preflight/activation_verification.json
.venv/bin/python tools/aggregate_preflight.py --output work/preflight/PREFLIGHT_GO.json
echo "PRE-FLIGHT PASS. You may now run windows\\02_start_f1.cmd."
