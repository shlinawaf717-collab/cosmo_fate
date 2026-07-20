#!/usr/bin/env python3
"""Estimate fate composition induced by each registered grammar and prior.

Flat coordinate priors are not identical function-space priors.  This audit
samples the actual P1 supports and model-specific early-matter-domination
conditions, then applies the same A-003 asymptotic epsilon used in the paper.
The GP entry is a construction, not a Monte Carlo prior estimate: its assigned
conditional-mean future has w_inf=-1 for every sample.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "runs/phase3/fparam/prior_fate_audit.json"
CLASSES = ("RIP", "DS", "DECAY")
EPSILON = 0.01


def summarize(labels: np.ndarray) -> dict:
    n = len(labels)
    result = {}
    for label in CLASSES:
        probability = float(np.mean(labels == label))
        result[label] = {
            "P": probability,
            "mc_se": float(np.sqrt(probability * (1.0 - probability) / n)),
        }
    result["n_accepted"] = n
    return result


def finite_limit_labels(w_inf: np.ndarray) -> np.ndarray:
    labels = np.full(len(w_inf), "DS", dtype="<U5")
    labels[w_inf < -1.0 - EPSILON] = "RIP"
    labels[w_inf > -1.0 + EPSILON] = "DECAY"
    return labels


def compute(n_proposals: int = 2_000_000, seed: int = 20260720) -> dict:
    rng = np.random.default_rng(seed)
    w = rng.uniform(-3.0, 1.0, n_proposals)
    wa = rng.uniform(-3.0, 2.0, n_proposals)

    allowed_cpl = w + wa < 0.0
    cpl_labels = np.where(wa[allowed_cpl] > 0.0, "RIP", "DECAY")

    allowed_bounded = w < 0.0
    jbp_labels = np.where(wa[allowed_bounded] > 0.0, "RIP", "DECAY")
    ba_labels = finite_limit_labels(w[allowed_bounded] - 0.5 * wa[allowed_bounded])

    w1 = rng.uniform(-3.0, 1.0, n_proposals)
    bin4_labels = finite_limit_labels(w1)

    return {
        "status": "exploratory post-hoc audit",
        "seed": seed,
        "n_proposals": n_proposals,
        "epsilon_A003": EPSILON,
        "warning": (
            "coordinate-wise flat priors, dimensions, constraints, and induced "
            "function-space measures differ across grammars"
        ),
        "models": {
            "CPL": {
                "support": "w0 in [-3,1], wa in [-3,2], conditioned on w0+wa<0",
                **summarize(cpl_labels),
            },
            "JBP": {
                "support": "w0 in [-3,1], wa in [-3,2], conditioned on w0<0",
                **summarize(jbp_labels),
            },
            "BA": {
                "support": "w0 in [-3,1], wa in [-3,2], conditioned on w0<0",
                **summarize(ba_labels),
            },
            "BIN4": {
                "support": "w1 in [-3,1]; independent early-time condition w4<0",
                **summarize(bin4_labels),
            },
            "GP_CONSTRUCTION": {
                "support": "assigned conditional-mean future w_inf=-1",
                "RIP": {"P": 0.0, "mc_se": 0.0},
                "DS": {"P": 1.0, "mc_se": 0.0},
                "DECAY": {"P": 0.0, "mc_se": 0.0},
                "n_accepted": None,
                "note": "deterministic construction; not a normalized fitted-prior estimate",
            },
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=2_000_000)
    parser.add_argument("--seed", type=int, default=20260720)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    result = compute(args.n, args.seed)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.output}")
    for name, row in result["models"].items():
        print(
            f"{name:15s} RIP={row['RIP']['P']:.4f} "
            f"DS={row['DS']['P']:.4f} DECAY={row['DECAY']['P']:.4f}"
        )


if __name__ == "__main__":
    main()
