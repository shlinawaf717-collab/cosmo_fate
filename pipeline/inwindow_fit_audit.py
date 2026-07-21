#!/usr/bin/env python3
"""Audit in-window fit quality for the four converged fitted grammars.

The reported minima are the lowest likelihood chi-square values found in the
archived post-burn-in chains, not dedicated optimizer results.  Delta AIC uses
only the dark-energy parameter-count difference because all nuisance and
background parameters are common.
"""

from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "runs/phase3/fparam/inwindow_fit_audit.json"
MODELS = {
    "CPL": {"root": "cpl", "k_dark": 2},
    "JBP": {"root": "jbp", "k_dark": 2},
    "BA": {"root": "ba", "k_dark": 2},
    "BIN4": {"root": "bin4", "k_dark": 4},
}


def chain_minimum(root: str, burn: float) -> tuple[float, list[str]]:
    files = sorted(glob.glob(str(ROOT / f"runs/phase3/fparam/{root}_*.1.txt")))
    if not files:
        raise FileNotFoundError(f"no archived chains found for {root}")
    minima = []
    for filename in files:
        with open(filename, encoding="utf-8") as handle:
            columns = handle.readline().lstrip("#").split()
        data = np.loadtxt(filename)
        data = data[int(burn * len(data)) :]
        minima.append(float(np.min(data[:, columns.index("chi2")])))
    return min(minima), [str(Path(name).relative_to(ROOT)) for name in files]


def gelman_rubin(root: str, burn: float) -> float:
    """Compute the multivariate GetDist R-1 diagnostic from archived chains."""
    from getdist import loadMCSamples
    samples = loadMCSamples(
        str(ROOT / f"runs/phase3/fparam/{root}"),
        settings={"ignore_rows": burn},
    )
    value = float(samples.getGelmanRubin())
    if not np.isfinite(value):
        raise ValueError(f"non-finite Gelman-Rubin diagnostic for {root}")
    return value


def compute(burn: float = 0.3) -> dict:
    rows = {}
    for name, spec in MODELS.items():
        chi2, files = chain_minimum(spec["root"], burn)
        rminus1 = gelman_rubin(spec["root"], burn)
        rows[name] = {
            "approx_chain_min_chi2": chi2,
            "k_dark": spec["k_dark"],
            "Rminus1_multivariate_recomputed": rminus1,
            "converged_registered_threshold": rminus1 < 0.01,
            "chains": files,
        }
    baseline = rows["CPL"]
    for row in rows.values():
        row["delta_chi2_vs_CPL"] = row["approx_chain_min_chi2"] - baseline["approx_chain_min_chi2"]
        row["delta_AIC_vs_CPL"] = (
            row["delta_chi2_vs_CPL"] + 2 * (row["k_dark"] - baseline["k_dark"])
        )
    return {
        "status": "exploratory post-hoc audit",
        "quantity": "lowest likelihood chi-square in archived post-burn-in chains",
        "caution": "not a dedicated optimizer or a model-evidence calculation",
        "burn_fraction": burn,
        "models": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--burn", type=float, default=0.3)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    result = compute(args.burn)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.output}")
    for name, row in result["models"].items():
        print(
            f"{name:4s} chi2={row['approx_chain_min_chi2']:.4f} "
            f"dchi2={row['delta_chi2_vs_CPL']:+.4f} "
            f"dAIC={row['delta_AIC_vs_CPL']:+.4f}"
        )


if __name__ == "__main__":
    main()
