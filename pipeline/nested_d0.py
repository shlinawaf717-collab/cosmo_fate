"""Nested-sampling verification for D0 (frozen plan §6):
- P(RIP) tail check (MCMC value must be verified before entering the paper)
- ln(Bayes factor) CPL vs LCDM on D0.

dynesty, nlive=500. Evidence normalization: the CPL run samples the full
[-3,1]x[-3,2] box with logL=-1e100 in the w0+wa>=0 dead zone; the frozen P1
prior is uniform on the ALLOWED region only, so lnZ_CPL gets the analytic
correction -ln(V_allowed/V_box) = -ln(15.5/20) = +0.25489.
"""

import sys, os, json
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

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
    info.pop('sampler'); info.pop('output')
    info['packages_path'] = os.path.join(ROOT, 'data/cobaya_packages')
    if model_kind == 'lcdm':
        info['params']['w'] = -1.0
        info['params']['wa'] = 0.0
        del info['prior']
        _names = NAMES_LCDM
    else:
        _names = NAMES_CPL
    import logging
    logging.disable(logging.WARNING)
    _model = get_model(info)


def _loglike(x):
    d = dict(zip(_names, x))
    if 'w' in d and (d['w'] + d['wa']) >= 0:
        return -1e100
    ll = _model.loglike(d, make_finite=True, return_derived=False)
    return ll if np.isfinite(ll) else -1e100


def _ptform(u, bounds):
    return np.array([lo + (hi - lo) * ui for ui, (lo, hi) in zip(u, bounds)])


def run(kind, nlive=500, nproc=3):
    import dynesty
    from functools import partial
    from multiprocessing import get_context
    bounds = BOUNDS_CPL if kind == 'cpl' else BOUNDS_LCDM
    ptform = partial(_ptform, bounds=bounds)
    ctx = get_context('spawn')
    with ctx.Pool(nproc, initializer=_init, initargs=(kind,)) as pool:
        _init(kind)  # local, for serial fallback paths inside dynesty
        s = dynesty.NestedSampler(
            _loglike, ptform, len(bounds),
            nlive=nlive, pool=pool, queue_size=nproc * 2)
        s.run_nested(dlogz=0.01, print_progress=False)
    r = s.results
    lnz, lnzerr = r.logz[-1], r.logzerr[-1]
    if kind == 'cpl':
        lnz += LN_VCORR
    # equal-weight posterior samples
    w = np.exp(r.logwt - r.logz[-1]); w /= w.sum()
    idx = np.random.default_rng(1).choice(len(w), size=min(20000, (w > 0).sum()),
                                          p=w, replace=True)
    samp = r.samples[idx]
    np.savez(os.path.join(ROOT, f'runs/phase2/nested_{kind}.npz'),
             samples=samp, names=np.array(BOUNDS_CPL if kind == 'cpl' else BOUNDS_LCDM),
             lnz=lnz, lnzerr=lnzerr, ncall=int(r.ncall.sum()))
    return lnz, lnzerr, samp


def main():
    out = {}
    lnz_c, err_c, samp = run('cpl')
    out['lnZ_CPL'] = lnz_c; out['lnZ_CPL_err'] = err_c
    print(f"CPL   lnZ = {lnz_c:.3f} +- {err_c:.3f}", flush=True)

    # fate classification on nested equal-weight samples
    from pipeline.fate import Background, classify
    from multiprocessing import get_context
    names = NAMES_CPL
    args = [(s[1], s[2], s[3], s[4]) for s in samp]  # omegam, H0, w, wa
    ctx = get_context('spawn')
    with ctx.Pool(6) as pool:
        labs = pool.starmap(_classify_one, args, chunksize=200)
    labs = np.array(labs)
    P = {L: float((labs == L).mean()) for L in ('CRUNCH', 'RIP', 'DS', 'DECAY', 'OTHER')}
    n = len(labs)
    out['P_fate_nested'] = P
    out['P_RIP_se_binom'] = float(np.sqrt(P['RIP'] * (1 - P['RIP']) / n))
    out['uncertainty_note'] = (
        'P_RIP_se_binom describes the fixed-seed equal-weight resample only; '
        'it is not repeated-run nested-sampling uncertainty'
    )
    print("nested fate P:", P, flush=True)

    lnz_l, err_l, _ = run('lcdm')
    out['lnZ_LCDM'] = lnz_l; out['lnZ_LCDM_err'] = err_l
    lnB = lnz_c - lnz_l
    out['lnB_CPL_over_LCDM'] = lnB
    out['lnB_err'] = float(np.hypot(err_c, err_l))
    print(f"LCDM  lnZ = {lnz_l:.3f} +- {err_l:.3f}", flush=True)
    print(f"lnB(CPL/LCDM) = {lnB:.3f} +- {out['lnB_err']:.3f}", flush=True)
    json.dump(out, open(os.path.join(ROOT, 'runs/phase2/nested_d0.json'), 'w'), indent=1)


def _classify_one(om, H0, w0, wa):
    from pipeline.fate import Background, classify
    lab, _ = classify(Background(omegam=om, H0=H0, w0=w0, wa=wa))
    return lab


if __name__ == '__main__':
    main()
