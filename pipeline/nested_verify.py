"""Nested-sampling re-verification of sub-percent P(RIP) tails (frozen plan §6).

Generic over run configs: builds the cobaya model from the run's own
input.yaml, nested-samples the posterior (logposterior over the uniform
sampled-parameter box, so Gaussian priors such as D2's BBN ombh2 and the
matter_dom / gp_kernel external priors are folded in automatically), and
classifies the equal-weight samples with the frozen fate criteria.

Usage: .venv/bin/python pipeline/nested_verify.py <input_yaml> <kind> <out_json>
       kind in {cpl, jbp}
"""

import json
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

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


def _classify_one(om, H0, w0, wa):
    from pipeline.fate import Background, classify
    if _kind == 'jbp':
        from pipeline.wparams import make_ln_fde, make_w_of_a, MODELS
        p = {'w': w0, 'wa': wa}
        bg = Background(omegam=om, H0=H0, ln_fde=make_ln_fde('jbp', p),
                        w_of_a=make_w_of_a('jbp', p),
                        w_inf=None)
    else:
        bg = Background(omegam=om, H0=H0, w0=w0, wa=wa)
    lab, _ = classify(bg)
    return lab


def _ptform(u, bounds):
    # module-level (picklable for the spawn pool; a main()-local closure is not)
    return np.array([lo + (hi - lo) * ui for ui, (lo, hi) in zip(u, bounds)])


def main(yaml_path, kind, out_path, nlive=500, nproc=3, maxiter=None):
    import dynesty
    from functools import partial
    from multiprocessing import get_context

    _init(yaml_path, kind)
    bounds = _model.prior.bounds(confidence_for_unbounded=0.9999)
    ndim = len(_names)
    ptform = partial(_ptform, bounds=bounds)

    ctx = get_context('spawn')
    with ctx.Pool(nproc, initializer=_init, initargs=(yaml_path, kind)) as pool:
        s = dynesty.NestedSampler(_logpost, ptform, ndim, nlive=nlive,
                                  pool=pool, queue_size=nproc * 2)
        s.run_nested(dlogz=0.01, print_progress=False, maxiter=maxiter)
    r = s.results
    w = np.exp(r.logwt - r.logz[-1]); w /= w.sum()
    idx = np.random.default_rng(1).choice(len(w), size=min(20000, int((w > 0).sum())),
                                          p=w, replace=True)
    samp = r.samples[idx]
    iom, iH0 = _names.index('omegam'), _names.index('H0')
    iw, iwa = _names.index('w'), _names.index('wa')

    labs = np.array([_classify_one(s_[iom], s_[iH0], s_[iw], s_[iwa])
                     for s_ in samp])
    P = {L: float((labs == L).mean())
         for L in ('CRUNCH', 'RIP', 'DS', 'DECAY', 'OTHER')}
    n = len(labs)
    out = {'yaml': os.path.relpath(yaml_path, ROOT), 'kind': kind,
           'nlive': nlive, 'ncall': int(r.ncall.sum()), 'n_samples': n,
           'P_fate_nested': P,
           'P_RIP_se_binom': float(np.sqrt(P['RIP'] * (1 - P['RIP']) / n))}
    json.dump(out, open(out_path, 'w'), indent=1)
    print(os.path.basename(out_path), 'P(RIP) =', P['RIP'],
          '+-', out['P_RIP_se_binom'], flush=True)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3])
