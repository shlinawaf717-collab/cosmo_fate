"""Classify fate over a posterior chain (frozen plan §5-§7).

Usage: .venv/bin/python pipeline/classify_posterior.py <chain_root> [out.json]

Reports per-class posterior probability with batch-means MC error (§6),
boundary-sample fraction (§5), and the thermodynamic mapping (§5).
"""

import sys, os, json
import numpy as np
from multiprocessing import Pool

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from pipeline.fate import Background, classify, THERMO

LABELS = ["CRUNCH", "RIP", "DS", "DECAY", "OTHER"]


def _worker(args):
    om, H0, w0, wa, omk = args
    lab, b = classify(Background(omegam=om, H0=H0, omk=omk, w0=w0, wa=wa))
    return lab, b


def main(root, out_path=None):
    from getdist import loadMCSamples
    s = loadMCSamples(root, settings={'ignore_rows': 0.3})
    names = [p.name for p in s.paramNames.names]
    def col(p):
        return s.samples[:, names.index(p)]
    om, H0, w0, wa = col('omegam'), col('H0'), col('w'), col('wa')
    omk = col('omk') if 'omk' in names else np.zeros_like(om)
    wts = s.weights
    n = len(wts)
    print(f"{n} post-burn-in samples from {root}")

    with Pool() as pool:
        res = pool.map(_worker, zip(om, H0, w0, wa, omk), chunksize=200)
    labs = np.array([r[0] for r in res])
    bnds = np.array([r[1] for r in res], dtype=bool)

    wtot = wts.sum()
    out = {"root": root, "n_samples": int(n)}
    print(f"\n{'class':8s} {'P':>9s} {'MC err':>9s}   thermo")
    B = 32
    edges = np.linspace(0, n, B + 1, dtype=int)
    for L in LABELS:
        sel = labs == L
        P = wts[sel].sum() / wtot
        # batch means over contiguous blocks (autocorrelation-aware)
        Pb = []
        for i in range(B):
            sl = slice(edges[i], edges[i + 1])
            wb = wts[sl]
            if wb.sum() > 0:
                Pb.append((wb * sel[sl]).sum() / wb.sum())
        se = np.std(Pb, ddof=1) / np.sqrt(len(Pb))
        out[L] = {"P": P, "mc_err": se}
        print(f"{L:8s} {P:9.5f} {se:9.5f}   {THERMO[L]}")

    bfrac = (wts * bnds).sum() / wtot
    heat = out["DS"]["P"] + out["DECAY"]["P"]
    out["boundary_fraction"] = bfrac
    out["P_heat_death_compatible"] = heat
    print(f"\nboundary-flagged fraction: {bfrac:.5f}")
    print(f"P(heat-death-compatible) = P(DS)+P(DECAY) = {heat:.5f}")
    print(f"P(non-heat-death) = P(RIP)+P(CRUNCH) = "
          f"{out['RIP']['P'] + out['CRUNCH']['P']:.5f}")
    if out["OTHER"]["P"] > 0.01:
        print("!! OTHER > 1% — frozen plan §5 requires criterion audit")

    if out_path:
        json.dump(out, open(out_path, 'w'), indent=1)
        print("written:", out_path)
    return out


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
