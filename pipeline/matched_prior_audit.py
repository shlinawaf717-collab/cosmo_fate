#!/usr/bin/env python3
"""Structural identifiability audit for a cross-grammar matched prior.

This post-hoc audit deliberately stops before importance weighting.  The four
registered grammar priors push forward onto lower-dimensional, different
linear supports in the seven-dimensional w(a) summary.  A full-dimensional
Gaussian density ratio is therefore not a Radon--Nikodym derivative of those
pushforward measures.  ESS and weight truncation cannot repair that failure.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "runs/phase3/fparam/matched_prior_audit.json"
METHOD_VERSION = "matched-prior-audit-v2-support-rank-no-go"
CLASSES = ("RIP", "DS", "DECAY")
EPSILON_A003 = 0.01
SUMMARY_A = np.array([0.5, 0.67, 0.8, 1.0, 1.5, 2.0, 4.0], dtype=float)
GRAMMARS = ("CPL", "JBP", "BA", "BIN4")


@dataclass(frozen=True)
class GrammarSamples:
    name: str
    summaries: np.ndarray
    labels: np.ndarray
    native_support: str


def fate_summary(labels: np.ndarray) -> dict[str, float]:
    """Return a stable, rounded simplex for contextual native-prior counts."""
    if len(labels) == 0:
        raise ValueError("labels must be non-empty")
    first = round(float(np.count_nonzero(labels == CLASSES[0]) / len(labels)), 12)
    second = round(float(np.count_nonzero(labels == CLASSES[1]) / len(labels)), 12)
    third = round(1.0 - first - second, 12)
    return {CLASSES[0]: first, CLASSES[1]: second, CLASSES[2]: third}


def finite_limit_labels(w_inf: np.ndarray) -> np.ndarray:
    labels = np.full(len(w_inf), "DS", dtype="<U5")
    labels[w_inf < -1.0 - EPSILON_A003] = "RIP"
    labels[w_inf > -1.0 + EPSILON_A003] = "DECAY"
    return labels


def support_basis(name: str) -> np.ndarray:
    """Return columns spanning a grammar's linear support in summary space."""
    a = SUMMARY_A
    ones = np.ones_like(a)
    lname = name.lower()
    if lname == "cpl":
        return np.column_stack([ones, 1.0 - a])
    if lname == "jbp":
        return np.column_stack([ones, a * (1.0 - a)])
    if lname == "ba":
        return np.column_stack([ones, (1.0 - a) / (2.0 * a**2 - 2.0 * a + 1.0)])
    if lname == "bin4":
        return np.array(
            [
                [0.0, 0.0, 0.0, 1.0],
                [0.0, 0.0, 1.0, 0.0],
                [0.0, 1.0, 0.0, 0.0],
                [1.0, 0.0, 0.0, 0.0],
                [1.0, 0.0, 0.0, 0.0],
                [1.0, 0.0, 0.0, 0.0],
                [1.0, 0.0, 0.0, 0.0],
            ]
        )
    raise ValueError(f"unknown grammar {name!r}")


def intrinsic_dimension(name: str) -> int:
    return int(np.linalg.matrix_rank(support_basis(name)))


def common_support_dimension(names: Iterable[str] = GRAMMARS) -> int:
    """Dimension of the intersection of the supplied column spaces."""
    complements = []
    ambient = len(SUMMARY_A)
    for name in names:
        basis = support_basis(name)
        u, _, _ = np.linalg.svd(basis, full_matrices=True)
        rank = np.linalg.matrix_rank(basis)
        complements.append(u[:, rank:].T)
    constraints = np.vstack(complements)
    return ambient - int(np.linalg.matrix_rank(constraints))


def draw_grammar(name: str, n: int, rng: np.random.Generator) -> GrammarSamples:
    """Draw native-prior samples only to report contextual native fate rates."""
    w = rng.uniform(-3.0, 1.0, n)
    wa = rng.uniform(-3.0, 2.0, n)
    lname = name.lower()
    if lname == "cpl":
        keep = w + wa < 0.0
        w, wa = w[keep], wa[keep]
        summaries = w[:, None] + wa[:, None] * (1.0 - SUMMARY_A)
        labels = np.where(wa > 0.0, "RIP", "DECAY")
        support = "w0 in [-3,1], wa in [-3,2], conditioned on w0+wa<0"
    elif lname == "jbp":
        keep = w < 0.0
        w, wa = w[keep], wa[keep]
        summaries = w[:, None] + wa[:, None] * SUMMARY_A[None, :] * (1.0 - SUMMARY_A[None, :])
        labels = np.where(wa > 0.0, "RIP", "DECAY")
        support = "w0 in [-3,1], wa in [-3,2], conditioned on w0<0"
    elif lname == "ba":
        keep = w < 0.0
        w, wa = w[keep], wa[keep]
        summaries = w[:, None] + wa[:, None] * (1.0 - SUMMARY_A[None, :]) / (
            2.0 * SUMMARY_A[None, :] ** 2 - 2.0 * SUMMARY_A[None, :] + 1.0
        )
        labels = finite_limit_labels(w - 0.5 * wa)
        support = "w0 in [-3,1], wa in [-3,2], conditioned on w0<0"
    elif lname == "bin4":
        w1 = rng.uniform(-3.0, 1.0, n)
        w2 = rng.uniform(-3.0, 1.0, n)
        w3 = rng.uniform(-3.0, 1.0, n)
        w4 = rng.uniform(-3.0, 1.0, n)
        keep = w4 < 0.0
        summaries = np.vstack([w4, w3, w2, w1, w1, w1, w1]).T[keep]
        labels = finite_limit_labels(w1[keep])
        support = "w1..w4 in [-3,1], conditioned on w4<0; w(a>1)=w1"
    else:
        raise ValueError(f"unknown grammar {name!r}")
    return GrammarSamples(name.upper(), summaries, labels.astype("<U5"), support)


def compute(n: int = 20000, seed: int = 20260720) -> dict:
    if n <= 0:
        raise ValueError("n must be positive")
    rng = np.random.default_rng(seed)
    grammars = [draw_grammar(name, n, rng) for name in GRAMMARS]
    ambient = len(SUMMARY_A)
    intersection_dim = common_support_dimension()
    rows = {}
    for grammar in grammars:
        dim = intrinsic_dimension(grammar.name)
        rows[grammar.name] = {
            "native_support": grammar.native_support,
            "native_fate_context_only": fate_summary(grammar.labels),
            "matched_fate": None,
            "no_go": True,
            "reason_code": "SINGULAR_PUSHFORWARD_SUPPORT",
            "diagnostics": {
                "n_accepted": int(len(grammar.labels)),
                "ambient_summary_dimension": ambient,
                "intrinsic_support_dimension": dim,
                "codimension": ambient - dim,
                "has_full_dimensional_density": False,
                "common_intersection_has_native_probability_zero": True,
                "ess": None,
                "support_overlap_fraction": None,
            },
        }

    return {
        "status": "DRAFT post-hoc structural audit; GLOBAL NO-GO; not preregistered and not signed",
        "method_version": METHOD_VERSION,
        "seed": seed,
        "n_proposals_per_grammar": n,
        "verdict": {
            "decision": "NO-GO",
            "exact_matched_prior_identifiable_by_importance_reweighting": False,
            "reason_code": "INCOMPATIBLE_SINGULAR_SUPPORTS",
            "reason": (
                "The native priors push forward to different lower-dimensional supports in the "
                "7D summary. No grammar has a 7D density, and their 1D common intersection has "
                "probability zero under every continuous native prior."
            ),
        },
        "input_sources": [
            "registered P1 coordinate supports encoded in pipeline/prior_fate_audit.py",
            "fixed-seed synthetic prior samples used only for native-fate context; no data likelihood, MCMC, or nested run",
        ],
        "common_object": {
            "candidate_summary_space": "w(a) evaluated on fixed grid",
            "a_grid": SUMMARY_A.tolist(),
            "ambient_dimension": ambient,
            "common_support_intersection_dimension": intersection_dim,
            "intersection_description": "constant histories w(a)=c on the declared grid",
            "admissible_importance_transport_measure": None,
        },
        "gate_order": [
            "structural support and absolute-continuity check",
            "only if structural gate passes: overlap, importance weights, truncation, and ESS",
        ],
        "warnings": [
            "The v1 pooled-Gaussian calculation is rejected: covariance regularization manufactured full-dimensional densities on singular supports.",
            "ESS and overlap numbers are intentionally withheld because the required density ratio does not exist.",
            "A future Go requires an explicit common generative prior plus grammar-specific pullback/conditioning, or a declared lower-dimensional estimand; it cannot be recovered by post-hoc reweighting of these native draws.",
        ],
        "grammars": rows,
    }


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=20000)
    parser.add_argument("--seed", type=int, default=20260720)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(list(argv) if argv is not None else None)
    result = compute(args.n, args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {args.output}")
    print(f"GLOBAL {result['verdict']['decision']}: {result['verdict']['reason_code']}")
    for name, row in result["grammars"].items():
        diag = row["diagnostics"]
        print(
            f"{name:5s} native={row['native_fate_context_only']} matched=None "
            f"support_dim={diag['intrinsic_support_dimension']}/{diag['ambient_summary_dimension']}"
        )


if __name__ == "__main__":
    main()
