"""Model-aware fate classification for the F_param axis."""
import sys, os, json
import numpy as np
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.fate import Background, classify
from pipeline.wparams import MODELS, make_ln_fde, make_w_of_a

LABELS = ["CRUNCH", "RIP", "DS", "DECAY", "OTHER"]
_model = None

def _init(model):
    global _model
    _model = model

def _worker(args):
    om, H0, mpars = args
    lf = make_ln_fde(_model, mpars)
    wf = make_w_of_a(_model, mpars)
    bg = Background(omegam=om, H0=H0, ln_fde=lf, w_of_a=wf)
    lab, b = classify(bg)
    return lab, b

def main(model, root, out_path):
    from getdist import loadMCSamples
    s = loadMCSamples(root, settings={'ignore_rows': 0.3})
    names = [p.name for p in s.paramNames.names]
    col = lambda p: s.samples[:, names.index(p)]
    om, H0, wts = col('omegam'), col('H0'), s.weights
    mp = MODELS[model]['params']
    mcols = {p: col(p) for p in mp}
    args = [(om[i], H0[i], {p: mcols[p][i] for p in mp}) for i in range(len(om))]
    with Pool(initializer=_init, initargs=(model,)) as pool:
        res = pool.map(_worker, args, chunksize=100)
    labs = np.array([r[0] for r in res]); bnds = np.array([r[1] for r in res])
    wtot = wts.sum()
    out = {'model': model, 'n': len(labs)}
    B = 32; edges = np.linspace(0, len(labs), B+1, dtype=int)
    for L in LABELS:
        sel = labs == L
        P = float(wts[sel].sum()/wtot)
        Pb = [(wts[a:b]*sel[a:b]).sum()/wts[a:b].sum() for a,b in zip(edges[:-1],edges[1:]) if wts[a:b].sum()>0]
        out[L] = {'P': P, 'mc_err': float(np.std(Pb, ddof=1)/np.sqrt(len(Pb)))}
    out['boundary_fraction'] = float((wts*bnds).sum()/wtot)
    out['P_heat'] = out['DS']['P'] + out['DECAY']['P']
    json.dump(out, open(out_path, 'w'), indent=1)
    print(model.upper(), {L: round(out[L]['P'], 4) for L in LABELS},
          'bnd:', round(out['boundary_fraction'], 4))

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3])
