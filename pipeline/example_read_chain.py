"""Minimal entry point for the released chains — reproduces Table I of the paper.
Run: .venv/bin/python pipeline/example_read_chain.py

Loads the D0 (DESI DR2 + CMB prior + Pantheon+SH0ES) CPL chains, prints the
marginal constraints, and pushes every posterior sample through the frozen
fate classifier (plan §5 / paper Sec. IV).
"""

import glob
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from pipeline.fate import Background, classify, THERMO

CHAINS = os.path.join(os.path.dirname(__file__), "..", "runs", "phase2", "mc", "d0*.txt")

rows, wts = [], []
for f in sorted(glob.glob(CHAINS)):
    if not f.split(".")[-2].isdigit():
        continue
    with open(f) as fh:
        cols = fh.readline().lstrip("#").split()
    d = np.loadtxt(f)
    d = d[int(0.3 * len(d)):]                      # burn-in
    rows.append(d[:, [cols.index(p) for p in ("omegam", "H0", "w", "wa")]])
    wts.append(d[:, cols.index("weight")])
X, w = np.concatenate(rows), np.concatenate(wts)

for i, name in enumerate(("Omega_m", "H0", "w0", "wa")):
    m = np.average(X[:, i], weights=w)
    s = np.sqrt(np.average((X[:, i] - m) ** 2, weights=w))
    print(f"{name:8s} = {m:8.4f} +- {s:.4f}")

# fate classification (thin for speed; full run uses every sample)
idx = np.random.default_rng(0).choice(len(X), 2000, p=w / w.sum())
counts = {}
for om, H0, w0, wa in X[idx]:
    label, _ = classify(Background(omegam=om, H0=H0, w0=w0, wa=wa))
    counts[label] = counts.get(label, 0) + 1
print("\nfate fractions (2000 weighted draws):")
for k, v in sorted(counts.items(), key=lambda kv: -kv[1]):
    print(f"  {k:6s} {v/2000:6.1%}  ({THERMO[k]})")
