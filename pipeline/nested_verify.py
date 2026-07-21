"""Thin CLI adapter for nested-sampling fate re-verification.

Usage: .venv/bin/python pipeline/nested_verify.py <input_yaml> <kind> <out_json>
       kind in {cpl, jbp}
"""

import os
import sys

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
    from cobaya.model import get_model
    from cobaya.yaml import yaml_load_file
    info = yaml_load_file(yaml_path)
    info.pop('sampler', None)
    info.pop('output', None)
    info['packages_path'] = os.path.join(ROOT, 'data/cobaya_packages')
    logging.disable(logging.WARNING)
    _model = get_model(info)
    _names = list(_model.parameterization.sampled_params())
    _kind = kind


def _logpost(x):
    lp = _model.logposterior(dict(zip(_names, x)), make_finite=True)
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


def main(yaml_path, kind, out_path, nlive=500, nproc=3, maxiter=None, seed=1):
    _init(yaml_path, kind)
    bounds = _model.prior.bounds(confidence_for_unbounded=0.9999)
    config = nc.NestedRunConfig(kind=kind, names=list(_names), bounds=list(map(tuple, bounds)),
                                nlive=nlive, nproc=nproc, maxiter=maxiter, seed=seed)
    results = nc.run_dynesty(config, _logpost, pool_initializer=_init, pool_initargs=(yaml_path, kind))
    samp, _, weights, ess = nc.resample_equal_weight(results.samples, results.logwt, results.logz[-1],
                                                     seed=seed, max_samples=config.max_samples)
    out = {'yaml': os.path.relpath(yaml_path, ROOT), 'kind': kind}
    out.update(nc.summarize_results(results, config))
    nc.add_resampling_audit(out, weights=weights, ess=ess, n_equal_weight=len(samp))
    probs, n = nc.classify_samples(samp, _names, _make_classifier(kind))
    nc.add_fate_summary(out, probs, n)
    nc.atomic_write_json(out_path, out, indent=1)
    print(os.path.basename(out_path), 'P(RIP) =', probs['RIP'], '+-', out['P_RIP_se_binom'], flush=True)


if __name__ == '__main__':
    if len(sys.argv) != 4:
        raise SystemExit('usage: nested_verify.py <input_yaml> <kind> <out_json>')
    main(sys.argv[1], sys.argv[2], sys.argv[3])
