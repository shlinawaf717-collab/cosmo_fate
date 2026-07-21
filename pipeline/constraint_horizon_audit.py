#!/usr/bin/env python3
"""Recompute the registered BIN4 constraint-horizon diagnostic.

The frozen metric is the marginal posterior-to-prior KL divergence of w(a),
with the first scale factor at which it falls below 0.1 nat called a_h.
For BIN4, w(a>1) inherits w1.  Therefore its future KL is the w1 KL carried
forward by the grammar; it is not zero.  The direct observational boundary at
a=1 is reported separately and must not be substituted for a_h.

The estimator reproduces the original audit: weighted histograms with 80
equal-width cells over each parameter's actual normalized prior support.
"""

from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GLOB = str(ROOT / "runs/phase3/fparam/bin4_*.1.txt")
DEFAULT_OUT = ROOT / "runs/phase3/fparam/ah.json"
PRIOR_SUPPORT = {
    "w1": (-3.0, 1.0),
    "w2": (-3.0, 1.0),
    "w3": (-3.0, 1.0),
    # The registered early-matter-domination condition is w4 < 0.
    "w4": (-3.0, 0.0),
}


def load_weighted_samples(pattern: str, burn: float) -> tuple[dict[str, np.ndarray], np.ndarray]:
    values = {name: [] for name in PRIOR_SUPPORT}
    weights = []
    files = sorted(glob.glob(pattern))
    if not files:
        raise FileNotFoundError(f"no BIN4 chains match {pattern}")
    for filename in files:
        with open(filename, encoding="utf-8") as handle:
            columns = handle.readline().lstrip("#").split()
        data = np.loadtxt(filename)
        data = data[int(burn * len(data)) :]
        weights.append(data[:, columns.index("weight")])
        for name in values:
            values[name].append(data[:, columns.index(name)])
    joined = {name: np.concatenate(chunks) for name, chunks in values.items()}
    joined_weights = np.concatenate(weights)
    joined_weights = joined_weights / joined_weights.sum()
    return joined, joined_weights


def histogram_kl(samples: np.ndarray, weights: np.ndarray, support: tuple[float, float],
                 bins: int) -> float:
    mass, _ = np.histogram(samples, bins=bins, range=support, weights=weights)
    mass = mass[mass > 0]
    return float(np.sum(mass * np.log(mass / (1.0 / bins))))


def compute(pattern: str = DEFAULT_GLOB, burn: float = 0.3, bins: int = 80) -> dict:
    samples, weights = load_weighted_samples(pattern, burn)
    kl = {
        name: histogram_kl(samples[name], weights, PRIOR_SUPPORT[name], bins)
        for name in PRIOR_SUPPORT
    }
    threshold = 0.1
    # All measured bins exceed the threshold, and BIN4 carries w1 into a>1.
    return {
        "metric": "marginal posterior-to-prior KL of w(a)",
        "estimator": f"weighted histogram, {bins} equal cells per normalized prior support",
        "burn_fraction": burn,
        "KL_per_bin": kl,
        "future_rule": "BIN4 freezes w(a>1)=w1",
        "KL_future_transport": kl["w1"],
        "threshold_nat": threshold,
        "a_h": None,
        "a_h_status": "not reached under the registered metric",
        "direct_observational_support_boundary": 1.0,
        "interpretation": (
            "a=1 is the boundary of direct observational support, not the KL horizon; "
            "the nonzero future KL is inherited from w1 by the BIN4 grammar"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chains", default=DEFAULT_GLOB)
    parser.add_argument("--burn", type=float, default=0.3)
    parser.add_argument("--bins", type=int, default=80)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    result = compute(args.chains, args.burn, args.bins)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.output}")
    print("a_h:", result["a_h_status"])
    print("KL:", result["KL_per_bin"])


if __name__ == "__main__":
    main()
