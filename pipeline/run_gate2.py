"""Gate-2 batch driver: run CPL+P1 pipeline on each mock, classify, log results.

Usage: .venv/bin/python pipeline/run_gate2.py [k_start k_end] [--jobs N]
Resume-safe: mocks with an existing result line in results.jsonl are skipped.
MCMC: 1 chain per mock (calibration machinery; paper chains use 4).
"""

import sys, os, json, subprocess, threading
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

MOCKS = os.path.join(ROOT, 'runs/gate2/mocks')
RESULTS = os.path.join(ROOT, 'runs/gate2/results.jsonl')
VENV_PY = os.path.join(ROOT, '.venv/bin/python')
COBAYA = os.path.join(ROOT, '.venv/bin/cobaya-run')

classify_lock = threading.Lock()
write_lock = threading.Lock()


def make_yaml(k):
    from cobaya.yaml import yaml_load_file, yaml_dump
    md = os.path.join(MOCKS, f'm{k:03d}')
    cmb_mean = json.load(open(f'{md}/cmb_mean.json'))['mean']
    info = yaml_load_file(os.path.join(HERE, 'd0_cpl_p1.yaml'))
    info['packages_path'] = os.path.join(ROOT, 'data/cobaya_packages')
    info['likelihood']['sn.pantheonplusshoes'] = {
        'path': md, 'dataset_file': 'config.dataset', 'use_abs_mag': True}
    info['likelihood']['bao.desi_dr2.desi_bao_all'] = {
        'path': md, 'measurements_file': 'bao_mean.txt',
        'cov_file': 'bao_cov.txt', 'rs_fid': 1}
    info['likelihood']['pipeline.cmb_distprior.PlanckDistPrior']['mean'] = cmb_mean
    info['sampler']['mcmc'].update(seed=3000 + k)
    info['sampler']['mcmc']['max_samples'] = 300000
    info['output'] = os.path.join(md, 'chain')
    y = os.path.join(md, 'run.yaml')
    open(y, 'w').write(yaml_dump(info))
    return md, y


def done_ks():
    ks = set()
    if os.path.exists(RESULTS):
        for line in open(RESULTS):
            try:
                ks.add(json.loads(line)['k'])
            except Exception:
                pass
    return ks


def run_one(k):
    md, y = make_yaml(k)
    chain_txt = os.path.join(md, 'chain.1.txt')
    log = os.path.join(md, 'run.log')
    if not os.path.exists(chain_txt) or os.path.exists(os.path.join(md, 'chain.checkpoint')):
        with open(log, 'w') as lf:
            r = subprocess.run([COBAYA, y, '--force'], stdout=lf, stderr=lf)
        if r.returncode != 0:
            return {"k": k, "error": f"cobaya exit {r.returncode}"}

    with classify_lock:
        from pipeline.classify_posterior import main as classify
        out = classify(os.path.join(md, 'chain'))
    rec = {"k": k,
           "P": {L: out[L]["P"] for L in ("CRUNCH", "RIP", "DS", "DECAY", "OTHER")},
           "mc_err": {L: out[L]["mc_err"] for L in ("CRUNCH", "RIP", "DS", "DECAY", "OTHER")},
           "P_heat": out["P_heat_death_compatible"],
           "boundary_fraction": out["boundary_fraction"],
           "n_samples": out["n_samples"]}
    with write_lock:
        with open(RESULTS, 'a') as f:
            f.write(json.dumps(rec) + '\n')
    return rec


def main(k0=1, k1=100, jobs=4):
    ks = [k for k in range(k0, k1 + 1) if k not in done_ks()]
    print(f"running {len(ks)} mocks with {jobs} workers")
    with ThreadPoolExecutor(max_workers=jobs) as ex:
        for rec in ex.map(run_one, ks):
            tag = 'ERR' if 'error' in rec else f"P_heat={rec['P_heat']:.4f} P_RIP={rec['P']['RIP']:.4f}"
            print(f"mock {rec['k']:3d}: {tag}", flush=True)


if __name__ == '__main__':
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    jobs = 4
    for x in sys.argv[1:]:
        if x.startswith('--jobs'):
            jobs = int(x.split('=')[1])
    k0, k1 = (int(a[0]), int(a[1])) if len(a) >= 2 else (1, 100)
    main(k0, k1, jobs)
