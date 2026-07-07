#!/bin/zsh
# Nested re-verification queue, 2-way parallel (frozen plan §6 sub-percent rule).
cd ~/cosmo_fate
while pgrep -f 'cobaya-run.*gp_' >/dev/null; do sleep 600; done
echo "[queue] GP chains done, starting nested verification $(date)"
run() { echo "[queue] $2 start $(date)"; .venv/bin/python pipeline/nested_verify.py "$1" "$3" "$2" || echo "[queue] $2 FAILED"; echo "[queue] $2 end $(date)"; }
# pair 1
run runs/phase3/fdata/d1_1.input.yaml  runs/phase3/fdata/nested_d1.json  cpl &
run runs/phase3/fdata/d2_1.input.yaml  runs/phase3/fdata/nested_d2.json  cpl &
wait
# pair 2
run runs/phase3/fdata/d3_1.input.yaml  runs/phase3/fdata/nested_d3.json  cpl &
run runs/phase3/fdata/d4_1.input.yaml  runs/phase3/fdata/nested_d4.json  cpl &
wait
# pair 3
run runs/phase3/fparam/cpl_1.input.yaml runs/phase3/fparam/nested_cpl_bgw.json cpl &
run runs/phase3/fparam/jbp_1.input.yaml runs/phase3/fparam/nested_jbp.json jbp &
wait
echo "[queue] all done $(date)"
