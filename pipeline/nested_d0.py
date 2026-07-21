"""D0 nested-sampling adapter using the shared nested interface."""

import os
import sys
from multiprocessing import get_context

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from pipeline import nested_core as nc

BOUNDS_CPL = [(0.005, 0.1), (0.01, 0.99), (20., 100.), (-3., 1.), (-3., 2.), (-20., -18.)]
NAMES_CPL = ['ombh2', 'omegam', 'H0', 'w', 'wa', 'Mb']
BOUNDS_LCDM = BOUNDS_CPL[:3] + [BOUNDS_CPL[5]]
NAMES_LCDM = ['ombh2', 'omegam', 'H0', 'Mb']
LN_VCORR = -np.log(15.5 / 20.0)   # w0+wa<0 keeps 15.5 of 20 units of (w0,wa) area

_model = None
_names = None


def _init(model_kind):
    global _model, _names
    from cobaya.model import get_model
    from cobaya.yaml import yaml_load_file
    info = yaml_load_file(os.path.join(ROOT, 'pipeline/d0_cpl_p1.yaml'))
    info.pop('sampler', None); info.pop('output', None)
    info['packages_path'] = os.path.join(ROOT, 'data/cobaya_packages')
    if model_kind == 'lcdm':
        info['params']['w'] = -1.0
        info['params']['wa'] = 0.0
        info.pop('prior', None)
        _names = NAMES_LCDM
    elif model_kind == 'cpl':
        _names = NAMES_CPL
    else:
        raise ValueError(f"unknown nested kind: {model_kind!r}")
    import logging
    logging.disable(logging.WARNING)
    _model = get_model(info)


def _loglike(x):
    d = dict(zip(_names, x))
    if 'w' in d and (d['w'] + d['wa']) >= 0:
        return -1e100
    ll = _model.loglike(d, make_finite=True, return_derived=False)
    return ll if np.isfinite(ll) else -1e100


def _classify_one(om, H0, w0, wa):
    from pipeline.fate import Background, classify
    lab, _ = classify(Background(omegam=om, H0=H0, w0=w0, wa=wa))
    return lab


def _d0_classifier(params):
    return _classify_one(params['omegam'], params['H0'], params['w'], params['wa'])


def _config(kind, nlive, nproc, seed):
    if kind == 'cpl':
        return nc.NestedRunConfig(kind='cpl', names=NAMES_CPL, bounds=BOUNDS_CPL, nlive=nlive,
                                  nproc=nproc, seed=seed, evidence_correction=float(LN_VCORR))
    if kind == 'lcdm':
        return nc.NestedRunConfig(kind='lcdm', names=NAMES_LCDM, bounds=BOUNDS_LCDM, nlive=nlive,
                                  nproc=nproc, seed=seed)
    raise ValueError(f"unknown nested kind: {kind!r}")


def run(kind, nlive=500, nproc=3, seed=1):
    config = _config(kind, nlive, nproc, seed)
    _init(kind)
    results = nc.run_dynesty(config, _loglike, pool_initializer=_init, pool_initargs=(kind,))
    samp, _, weights, ess = nc.resample_equal_weight(results.samples, results.logwt, results.logz[-1],
                                                     seed=seed, max_samples=config.max_samples)
    summary = nc.summarize_results(results, config)
    nc.add_resampling_audit(summary, weights=weights, ess=ess, n_equal_weight=len(samp))
    np.savez(os.path.join(ROOT, f'runs/phase2/nested_{kind}.npz'),
             samples=samp, names=np.array(config.names), bounds=np.array(config.bounds),
             lnz=summary['logZ'], lnzerr=summary['logZerr'], ncall=summary['ncall'],
             schema_version=nc.SCHEMA_VERSION, seed=seed, ess=ess)
    return summary['logZ'], summary['logZerr'], samp, summary


def main():
    out = {'schema_version': nc.SCHEMA_VERSION, 'seed': 1, 'resampling_method': nc.RESAMPLING_METHOD}
    lnz_c, err_c, samp, meta_c = run('cpl')
    out['lnZ_CPL'] = lnz_c; out['lnZ_CPL_err'] = err_c
    out['CPL_audit'] = meta_c
    print(f"CPL   lnZ = {lnz_c:.3f} +- {err_c:.3f}", flush=True)

    ctx = get_context('spawn')
    args = [(s[1], s[2], s[3], s[4]) for s in samp]
    with ctx.Pool(6) as pool:
        labs = pool.starmap(_classify_one, args, chunksize=200)
    probs = {L: float((np.array(labs) == L).mean()) for L in nc.FATE_LABELS}
    nc.add_fate_summary(out, probs, len(labs))
    print("nested fate P:", probs, flush=True)

    lnz_l, err_l, _, meta_l = run('lcdm')
    out['lnZ_LCDM'] = lnz_l; out['lnZ_LCDM_err'] = err_l
    out['LCDM_audit'] = meta_l
    out['ncall'] = {'cpl': meta_c['ncall'], 'lcdm': meta_l['ncall']}
    out['ess'] = {'cpl': meta_c['ess'], 'lcdm': meta_l['ess']}
    out['n_samples'] = {'cpl': meta_c['n_samples'], 'lcdm': meta_l['n_samples']}
    out['lnB_CPL_over_LCDM'] = lnz_c - lnz_l
    out['lnB_err'] = float(np.hypot(err_c, err_l))
    print(f"LCDM  lnZ = {lnz_l:.3f} +- {err_l:.3f}", flush=True)
    print(f"lnB(CPL/LCDM) = {out['lnB_CPL_over_LCDM']:.3f} +- {out['lnB_err']:.3f}", flush=True)
    nc.atomic_write_json(os.path.join(ROOT, 'runs/phase2/nested_d0.json'), out, indent=1)


if __name__ == '__main__':
    main()
