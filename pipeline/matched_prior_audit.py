#!/usr/bin/env python3
"""Post-hoc matched-prior sensitivity audit for fate grammars.

This pilot does not run MCMC/nested sampling and does not claim preregistered
status.  It draws fixed-seed synthetic samples from the registered P1 native
coordinate supports, maps each draw into a common function-summary space, and
uses importance reweighting toward a common Gaussian summary target.  If support
or effective sample size diagnostics fail, the matched row is marked No-Go.
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
METHOD_VERSION = "matched-prior-pilot-v1"
CLASSES = ("RIP", "DS", "DECAY")
EPSILON_A003 = 0.01
SUMMARY_A = np.array([0.5, 0.67, 0.8, 1.0, 1.5, 2.0, 4.0], dtype=float)
DEFAULT_MIN_ESS_FRACTION = 0.05
DEFAULT_MIN_OVERLAP = 0.20
DEFAULT_TRUNCATION_QUANTILE = 0.995


@dataclass(frozen=True)
class GrammarSamples:
    name: str
    summaries: np.ndarray
    labels: np.ndarray
    native_support: str


def normalize_weights(raw: np.ndarray) -> np.ndarray:
    raw = np.asarray(raw, dtype=float)
    if raw.ndim != 1 or raw.size == 0:
        raise ValueError("weights must be a non-empty one-dimensional array")
    if np.any(raw < 0) or not np.all(np.isfinite(raw)):
        raise ValueError("weights must be finite and non-negative")
    total = float(raw.sum())
    if total <= 0.0:
        raise ValueError("at least one weight must be positive")
    return raw / total


def ess(weights: np.ndarray) -> float:
    w = normalize_weights(weights)
    return float(1.0 / np.sum(w * w))


def fate_summary(labels: np.ndarray, weights: np.ndarray | None = None) -> dict[str, float]:
    if weights is None:
        weights = np.full(len(labels), 1.0 / len(labels))
    else:
        weights = normalize_weights(weights)
    out = {klass: float(weights[labels == klass].sum()) for klass in CLASSES}
    # absorb roundoff so machine checks see an exact simplex to typical tolerances
    out[CLASSES[-1]] = float(1.0 - sum(out[k] for k in CLASSES[:-1]))
    return out


def finite_limit_labels(w_inf: np.ndarray) -> np.ndarray:
    labels = np.full(len(w_inf), "DS", dtype="<U5")
    labels[w_inf < -1.0 - EPSILON_A003] = "RIP"
    labels[w_inf > -1.0 + EPSILON_A003] = "DECAY"
    return labels


def draw_grammar(name: str, n: int, rng: np.random.Generator) -> GrammarSamples:
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
        summaries = w[:, None] + wa[:, None] * (1.0 - SUMMARY_A[None, :]) / (2.0 * SUMMARY_A[None, :] ** 2 - 2.0 * SUMMARY_A[None, :] + 1.0)
        labels = finite_limit_labels(w - 0.5 * wa)
        support = "w0 in [-3,1], wa in [-3,2], conditioned on w0<0"
    elif lname == "bin4":
        w1 = rng.uniform(-3.0, 1.0, n)
        w2 = rng.uniform(-3.0, 1.0, n)
        w3 = rng.uniform(-3.0, 1.0, n)
        w4 = rng.uniform(-3.0, 1.0, n)
        keep = w4 < 0.0
        vals = np.vstack([w4, w3, w2, w1, w1, w1, w1]).T
        summaries = vals[keep]
        labels = finite_limit_labels(w1[keep])
        support = "w1..w4 in [-3,1], conditioned on w4<0; w(a>1)=w1"
    else:
        raise ValueError(f"unknown grammar {name!r}")
    return GrammarSamples(name.upper(), summaries, labels.astype("<U5"), support)


def _regularized_cov(samples: np.ndarray) -> np.ndarray:
    cov = np.cov(samples, rowvar=False)
    scale = float(np.trace(cov) / cov.shape[0]) if cov.ndim == 2 else 1.0
    return cov + np.eye(cov.shape[0]) * max(scale * 1e-6, 1e-8)


def gaussian_logpdf(x: np.ndarray, mean: np.ndarray, cov: np.ndarray) -> np.ndarray:
    inv = np.linalg.pinv(cov)
    diff = x - mean
    return -0.5 * np.einsum("ij,jk,ik->i", diff, inv, diff)


def weighted_quantile(values: np.ndarray, weights: np.ndarray, q: float) -> float:
    order = np.argsort(values)
    v = values[order]
    w = normalize_weights(weights[order])
    return float(v[np.searchsorted(np.cumsum(w), q, side="left")])


def matched_weights(samples: GrammarSamples, target_mean: np.ndarray, target_cov: np.ndarray, truncation_quantile: float) -> tuple[np.ndarray, dict]:
    native_cov = _regularized_cov(samples.summaries)
    logw = gaussian_logpdf(samples.summaries, target_mean, target_cov) - gaussian_logpdf(samples.summaries, samples.summaries.mean(axis=0), native_cov)
    logw -= float(np.max(logw))
    raw = np.exp(logw)
    untruncated = normalize_weights(raw)
    cap = weighted_quantile(untruncated, untruncated, truncation_quantile)
    truncated = normalize_weights(np.minimum(untruncated, cap))
    diagnostics = {
        "ess_raw": ess(untruncated),
        "ess_truncated": ess(truncated),
        "max_weight_raw": float(np.max(untruncated)),
        "max_weight_truncated": float(np.max(truncated)),
        "truncation_quantile": truncation_quantile,
        "truncation_cap": float(cap),
    }
    return truncated, diagnostics


def compute(n: int = 20000, seed: int = 20260720, min_ess_fraction: float = DEFAULT_MIN_ESS_FRACTION, min_overlap: float = DEFAULT_MIN_OVERLAP, truncation_quantile: float = DEFAULT_TRUNCATION_QUANTILE) -> dict:
    rng = np.random.default_rng(seed)
    grammars = [draw_grammar(g, n, rng) for g in ("CPL", "JBP", "BA", "BIN4")]
    pooled = np.vstack([g.summaries for g in grammars])
    target_mean = pooled.mean(axis=0)
    target_cov = _regularized_cov(pooled)
    rows = {}
    warnings = []
    for g in grammars:
        w, diag = matched_weights(g, target_mean, target_cov, truncation_quantile)
        overlap = float(np.mean(gaussian_logpdf(g.summaries, target_mean, target_cov) >= np.quantile(gaussian_logpdf(pooled, target_mean, target_cov), 0.05)))
        diag.update({"support_overlap_fraction": overlap, "n_accepted": int(len(g.labels)), "ess_fraction": float(diag["ess_truncated"] / len(g.labels))})
        no_go = diag["ess_fraction"] < min_ess_fraction or overlap < min_overlap
        if no_go:
            warnings.append(f"{g.name}: No-Go matched prior; insufficient ESS or support overlap")
        rows[g.name] = {"native_support": g.native_support, "native_fate": fate_summary(g.labels), "matched_fate": None if no_go else fate_summary(g.labels, w), "diagnostics": diag, "no_go": no_go}
    return {"status": "DRAFT post-hoc matched-prior audit; not preregistered and not signed", "method_version": METHOD_VERSION, "seed": seed, "n_proposals_per_grammar": n, "input_sources": ["registered P1 coordinate supports encoded in pipeline/prior_fate_audit.py", "fixed-seed synthetic prior samples only; no new data and no MCMC/nested run"], "common_object": {"summary_space": "w(a) evaluated on fixed grid", "a_grid": SUMMARY_A.tolist(), "measure": "importance transport to pooled Gaussian reference in summary space"}, "thresholds": {"min_ess_fraction": min_ess_fraction, "min_support_overlap_fraction": min_overlap}, "warnings": warnings, "grammars": rows}


def main(argv: Iterable[str] | None = None) -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, default=20000)
    p.add_argument("--seed", type=int, default=20260720)
    p.add_argument("--output", type=Path, default=DEFAULT_OUT)
    p.add_argument("--min-ess-fraction", type=float, default=DEFAULT_MIN_ESS_FRACTION)
    p.add_argument("--min-overlap", type=float, default=DEFAULT_MIN_OVERLAP)
    args = p.parse_args(list(argv) if argv is not None else None)
    result = compute(args.n, args.seed, args.min_ess_fraction, args.min_overlap)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {args.output}")
    for name, row in result["grammars"].items():
        print(f"{name:5s} native={row['native_fate']} matched={row['matched_fate']} no_go={row['no_go']} ESS={row['diagnostics']['ess_truncated']:.1f}")


if __name__ == "__main__":
    main()
