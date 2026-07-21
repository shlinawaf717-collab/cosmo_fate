"""Model-aware fate classification for the F_param axis."""
import sys, os, json, glob
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
    wi = MODELS[_model]['w_inf']
    bg = Background(omegam=om, H0=H0, ln_fde=lf, w_of_a=wf,
                    w_inf=(wi(mpars) if wi else None))
    lab, b = classify(bg)
    return lab, b


def load_release_columns(root, required, burn=0.3):
    """Load only archived text chains, independent of ignored sidecar files."""
    files = sorted(glob.glob(f"{root}_*.1.txt"))
    if not files:
        raise FileNotFoundError(f"no release chains found for {root}")
    values = {name: [] for name in required}
    weights = []
    for filename in files:
        with open(filename, encoding="utf-8") as handle:
            columns = handle.readline().lstrip("#").split()
        data = np.loadtxt(filename)
        data = data[int(burn * len(data)) :]
        for name in required:
            values[name].append(data[:, columns.index(name)])
        weights.append(data[:, columns.index("weight")])
    return {name: np.concatenate(parts) for name, parts in values.items()}, np.concatenate(weights)

def main(model, root, out_path):
    mp = MODELS[model]['params']
    columns, wts = load_release_columns(root, ["omegam", "H0", *mp])
    om, H0 = columns["omegam"], columns["H0"]
    mcols = {p: columns[p] for p in mp}
    args = [(om[i], H0[i], {p: mcols[p][i] for p in mp}) for i in range(len(om))]
    with Pool(initializer=_init, initargs=(model,)) as pool:
        res = pool.map(_worker, args, chunksize=100)
    labs = np.array([r[0] for r in res]); bnds = np.array([r[1] for r in res])
    wtot = wts.sum()
    out = {
        'model': model,
        'n': len(labs),
        'method': 'A-005 exact finite-limit fate semantics',
        'boundary_definition': '|w_inf + 1| <= 0.01 for finite-limit models; threshold variation otherwise',
    }
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
