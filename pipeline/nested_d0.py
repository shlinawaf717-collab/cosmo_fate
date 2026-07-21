"""D0 nested-sampling adapter using original weights and explicit seeds."""

import argparse
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
    # Reject the part of the rectangular sampling box that implies negative
    # cold-dark-matter density before calling CAMB. CAMB already assigns these
    # points zero likelihood; the guard is therefore measure-preserving but
    # avoids an expensive recombination calculation and noisy Fortran warnings.
    omch2 = d['omegam'] * (d['H0'] / 100.0) ** 2 - d['ombh2'] - 0.06 / 93.14
    if omch2 <= 0.0:
        return -1e100
    ll = _model.loglike(d, make_finite=True, return_derived=False)
    return ll if np.isfinite(ll) else -1e100


def _classify_one(om, H0, w0, wa):
    from pipeline.fate import Background, classify
    lab, _ = classify(Background(omegam=om, H0=H0, w0=w0, wa=wa))
    return lab


def _d0_classifier(params):
    return _classify_one(params['omegam'], params['H0'], params['w'], params['wa'])


def _config(kind, nlive, nproc, seed, maxiter=None, dlogz=0.01):
    if kind == 'cpl':
        return nc.NestedRunConfig(kind='cpl', names=NAMES_CPL, bounds=BOUNDS_CPL, nlive=nlive,
                                  nproc=nproc, seed=seed, maxiter=maxiter, dlogz=dlogz,
                                  evidence_correction=float(LN_VCORR))
    if kind == 'lcdm':
        return nc.NestedRunConfig(kind='lcdm', names=NAMES_LCDM, bounds=BOUNDS_LCDM, nlive=nlive,
                                  nproc=nproc, seed=seed, maxiter=maxiter, dlogz=dlogz)
    raise ValueError(f"unknown nested kind: {kind!r}")


def run(kind, nlive=500, nproc=3, seed=1, maxiter=None, dlogz=0.01):
    config = _config(kind, nlive, nproc, seed, maxiter=maxiter, dlogz=dlogz)
    _init(kind)
    results = nc.run_dynesty(config, _loglike, pool_initializer=_init, pool_initargs=(kind,))
    samp, indices, weights, ess = nc.resample_equal_weight(
        results.samples, results.logwt, results.logz[-1], seed=seed,
        max_samples=config.max_samples
    )
    summary = nc.summarize_results(results, config)
    nc.add_resampling_audit(summary, weights=weights, ess=ess, n_equal_weight=len(samp))
    return results, weights, indices, samp, summary, config


def main(seed=1, nlive=500, nproc=3, classify_nproc=6, maxiter=None, dlogz=0.01,
         output_path=None, archive_prefix=None):
    output_path = output_path or os.path.join(ROOT, f'runs/phase2/nested_d0_seed{seed}.json')
    archive_prefix = archive_prefix or os.path.join(ROOT, f'runs/phase2/nested_seed{seed}')
    out = {'schema_version': nc.SCHEMA_VERSION, 'seed': seed,
           'resampling_method': nc.RESAMPLING_METHOD,
           'headline_fate_estimator': 'normalized original nested weights'}
    results_c, weights_c, indices_c, samp, meta_c, config_c = run(
        'cpl', nlive=nlive, nproc=nproc, seed=seed, maxiter=maxiter, dlogz=dlogz
    )
    lnz_c, err_c = meta_c['logZ'], meta_c['logZerr']
    out['lnZ_CPL'] = lnz_c; out['lnZ_CPL_err'] = err_c
    out['CPL_audit'] = meta_c
    print(f"CPL   lnZ = {lnz_c:.3f} +- {err_c:.3f}", flush=True)

    ctx = get_context('spawn')
    args = [(s[1], s[2], s[3], s[4]) for s in results_c.samples]
    with ctx.Pool(classify_nproc) as pool:
        labs = pool.starmap(_classify_one, args, chunksize=200)
    labs = np.asarray(labs, dtype='<U6')
    probs = nc.probabilities_from_labels(labs, weights_c)
    equal_probs = nc.probabilities_from_labels(labs[indices_c])
    counts = {label: int(np.count_nonzero(labs == label)) for label in nc.FATE_LABELS}
    nc.add_fate_summary(out, probs, len(indices_c),
                        equal_weight_probabilities=equal_probs, raw_label_counts=counts)
    nc.save_nested_archive(f'{archive_prefix}_cpl.npz', results_c, config_c, weights_c,
                           indices_c, meta_c, labels=labs)
    print("nested fate P:", probs, flush=True)

    results_l, weights_l, indices_l, _, meta_l, config_l = run(
        'lcdm', nlive=nlive, nproc=nproc, seed=seed, maxiter=maxiter, dlogz=dlogz
    )
    lnz_l, err_l = meta_l['logZ'], meta_l['logZerr']
    nc.save_nested_archive(f'{archive_prefix}_lcdm.npz', results_l, config_l, weights_l,
                           indices_l, meta_l)
    out['lnZ_LCDM'] = lnz_l; out['lnZ_LCDM_err'] = err_l
    out['LCDM_audit'] = meta_l
    out['ncall'] = {'cpl': meta_c['ncall'], 'lcdm': meta_l['ncall']}
    out['ess'] = {'cpl': meta_c['ess'], 'lcdm': meta_l['ess']}
    out['n_samples'] = {'cpl': meta_c['n_samples'], 'lcdm': meta_l['n_samples']}
    out['lnB_CPL_over_LCDM'] = lnz_c - lnz_l
    out['lnB_err'] = float(np.hypot(err_c, err_l))
    print(f"LCDM  lnZ = {lnz_l:.3f} +- {err_l:.3f}", flush=True)
    print(f"lnB(CPL/LCDM) = {out['lnB_CPL_over_LCDM']:.3f} +- {out['lnB_err']:.3f}", flush=True)
    nc.atomic_write_json(output_path, out, indent=1)
    return out


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, default=1)
    parser.add_argument('--nlive', type=int, default=500)
    parser.add_argument('--nproc', type=int, default=3)
    parser.add_argument('--classify-nproc', type=int, default=6)
    parser.add_argument('--maxiter', type=int)
    parser.add_argument('--dlogz', type=float, default=0.01)
    parser.add_argument('--output')
    parser.add_argument('--archive-prefix')
    args = parser.parse_args()
    main(seed=args.seed, nlive=args.nlive, nproc=args.nproc,
         classify_nproc=args.classify_nproc, maxiter=args.maxiter,
         dlogz=args.dlogz, output_path=args.output,
         archive_prefix=args.archive_prefix)
