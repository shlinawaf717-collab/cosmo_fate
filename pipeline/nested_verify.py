"""Thin CLI adapter for weighted nested-sampling fate re-verification.

Usage: .venv/bin/python pipeline/nested_verify.py <input_yaml> <kind> <out_json>
       kind in {cpl, jbp}
"""

import argparse
import os
import sys
from multiprocessing import get_context

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from pipeline import nested_core as nc

_model = None
_names = None
_kind = None


def _init(yaml_path, kind):
    global _model, _names, _kind
    import logging
    import warnings
    from cobaya.model import get_model
    from cobaya.yaml import yaml_load_file
    info = yaml_load_file(yaml_path)
    info.pop('sampler', None)
    info.pop('output', None)
    info['packages_path'] = os.path.join(ROOT, 'data/cobaya_packages')
    logging.disable(logging.WARNING)
    warnings.filterwarnings(
        "ignore", message="overflow encountered in scalar add",
        category=RuntimeWarning, module=r"cobaya\.model",
    )
    _model = get_model(info)
    _names = list(_model.parameterization.sampled_params())
    _kind = kind


def _logpost(x):
    params = dict(zip(_names, x))
    if {"ombh2", "omegam", "H0"}.issubset(params):
        omch2 = params["omegam"] * (params["H0"] / 100.0) ** 2 \
            - params["ombh2"] - 0.06 / 93.14
        if omch2 <= 0.0:
            return -1e100
    lp = _model.logposterior(params, make_finite=True)
    v = lp.logpost
    return v if np.isfinite(v) else -1e100


def _make_classifier(kind):
    if kind not in ('cpl', 'jbp'):
        raise ValueError(f"unknown nested kind: {kind!r}")

    def classify_params(params):
        from pipeline.fate import Background, classify
        if kind == 'jbp':
            from pipeline.wparams import make_ln_fde, make_w_of_a
            p = {'w': params['w'], 'wa': params['wa']}
            bg = Background(omegam=params['omegam'], H0=params['H0'],
                            ln_fde=make_ln_fde('jbp', p), w_of_a=make_w_of_a('jbp', p),
                            w_inf=None)
        else:
            bg = Background(omegam=params['omegam'], H0=params['H0'], w0=params['w'], wa=params['wa'])
        lab, _ = classify(bg)
        return lab

    return classify_params


def _init_classifier(names, kind):
    global _names, _kind
    _names = list(names)
    _kind = kind


def _classify_row(row):
    return _make_classifier(_kind)(dict(zip(_names, map(float, row))))


def main(yaml_path, kind, out_path, nlive=500, nproc=3, maxiter=None, seed=1,
         archive_path=None, classify_nproc=3):
    if classify_nproc <= 0:
        raise ValueError("classify_nproc must be positive")
    _init(yaml_path, kind)
    bounds = _model.prior.bounds(confidence_for_unbounded=0.9999)
    config = nc.NestedRunConfig(kind=kind, names=list(_names), bounds=list(map(tuple, bounds)),
                                nlive=nlive, nproc=nproc, maxiter=maxiter, seed=seed)
    results = nc.run_dynesty(config, _logpost, pool_initializer=_init, pool_initargs=(yaml_path, kind))
    samp, indices, weights, ess = nc.resample_equal_weight(
        results.samples, results.logwt, results.logz[-1], seed=seed,
        max_samples=config.max_samples
    )
    out = {'yaml': os.path.relpath(yaml_path, ROOT), 'kind': kind}
    out.update(nc.summarize_results(results, config))
    nc.add_resampling_audit(out, weights=weights, ess=ess, n_equal_weight=len(samp))
    if classify_nproc == 1:
        labels = np.asarray([_classify_row(row) for row in results.samples], dtype="<U6")
    else:
        ctx = get_context("spawn")
        with ctx.Pool(classify_nproc, initializer=_init_classifier,
                      initargs=(list(_names), kind)) as pool:
            labels = np.asarray(pool.map(_classify_row, results.samples, chunksize=200),
                                dtype="<U6")
    probs = nc.probabilities_from_labels(labels, weights)
    counts = {label: int(np.count_nonzero(labels == label)) for label in nc.FATE_LABELS}
    equal_probs = nc.probabilities_from_labels(labels[indices])
    nc.add_fate_summary(out, probs, len(indices),
                        equal_weight_probabilities=equal_probs,
                        raw_label_counts=counts)
    archive_path = archive_path or os.path.splitext(out_path)[0] + '.npz'
    nc.save_nested_archive(archive_path, results, config, weights, indices, out,
                           labels=labels)
    nc.atomic_write_json(out_path, out, indent=1)
    print(os.path.basename(out_path), 'P(RIP) =', probs['RIP'], '+-', out['P_RIP_se_binom'], flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('input_yaml')
    parser.add_argument('kind', choices=('cpl', 'jbp'))
    parser.add_argument('out_json')
    parser.add_argument('--nlive', type=int, default=500)
    parser.add_argument('--nproc', type=int, default=3)
    parser.add_argument('--classify-nproc', type=int, default=3)
    parser.add_argument('--maxiter', type=int)
    parser.add_argument('--seed', type=int, default=1)
    parser.add_argument('--archive')
    args = parser.parse_args()
    main(args.input_yaml, args.kind, args.out_json, nlive=args.nlive,
         nproc=args.nproc, maxiter=args.maxiter, seed=args.seed,
         archive_path=args.archive, classify_nproc=args.classify_nproc)
