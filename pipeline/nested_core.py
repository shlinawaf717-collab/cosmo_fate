"""Shared nested-sampling interface utilities.

This module keeps dynesty/cobaya-specific work behind callables so tests can
exercise prior transforms, result normalization, resampling, classification,
and serialization without importing heavy cosmology dependencies.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from typing import Callable, Mapping, Sequence

import numpy as np

SCHEMA_VERSION = "nested-interface-v1"
FATE_LABELS = ("CRUNCH", "RIP", "DS", "DECAY", "OTHER")
RESAMPLING_METHOD = "fixed-seed-multinomial-logwt"
UNCERTAINTY_NOTE = (
    "P_RIP_se_binom describes the fixed-seed equal-weight resample only; "
    "it is not repeated-run nested-sampling uncertainty"
)


@dataclass(frozen=True)
class NestedRunConfig:
    kind: str
    names: Sequence[str]
    bounds: Sequence[tuple[float, float]]
    nlive: int = 500
    nproc: int = 3
    seed: int = 1
    max_samples: int = 20000
    dlogz: float = 0.01
    maxiter: int | None = None
    evidence_correction: float = 0.0

    def validate(self) -> None:
        if len(self.names) != len(self.bounds):
            raise ValueError("names and bounds must have the same length")
        if self.kind not in ("cpl", "lcdm", "jbp"):
            raise ValueError(f"unknown nested kind: {self.kind!r}")
        if self.nlive <= 0 or self.nproc <= 0 or self.max_samples <= 0:
            raise ValueError("nlive, nproc and max_samples must be positive")
        for lo, hi in self.bounds:
            if not (np.isfinite(lo) and np.isfinite(hi) and hi > lo):
                raise ValueError(f"invalid bound ({lo}, {hi})")


def prior_transform(u: Sequence[float], bounds: Sequence[tuple[float, float]]) -> np.ndarray:
    u = np.asarray(u, dtype=float)
    if len(u) != len(bounds):
        raise ValueError("unit cube vector length does not match bounds")
    if np.any(~np.isfinite(u)) or np.any((u < 0.0) | (u > 1.0)):
        raise ValueError("prior transform expects finite values in [0, 1]")
    return np.array([lo + (hi - lo) * ui for ui, (lo, hi) in zip(u, bounds)], dtype=float)


def stable_normalized_weights(logwt: Sequence[float], logz_final: float | None = None) -> tuple[np.ndarray, float]:
    lw = np.asarray(logwt, dtype=float)
    finite = np.isfinite(lw)
    if not np.any(finite):
        raise ValueError("all nested log weights are non-finite")
    shifted = np.full_like(lw, -np.inf, dtype=float)
    center = float(logz_final) if logz_final is not None and np.isfinite(logz_final) else float(np.max(lw[finite]))
    shifted[finite] = lw[finite] - center
    max_shift = float(np.max(shifted[finite]))
    raw = np.exp(shifted - max_shift)
    raw[~np.isfinite(raw)] = 0.0
    total = float(raw.sum())
    if not np.isfinite(total) or total <= 0.0:
        raise ValueError("nested log weights normalize to zero or non-finite total")
    w = raw / total
    ess = float(1.0 / np.sum(w * w))
    return w, ess


def resample_equal_weight(samples: Sequence[Sequence[float]], logwt: Sequence[float], logz_final: float | None,
                          *, seed: int, max_samples: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    samples = np.asarray(samples, dtype=float)
    if samples.ndim != 2:
        raise ValueError("samples must be a 2D array")
    weights, ess = stable_normalized_weights(logwt, logz_final)
    if len(weights) != len(samples):
        raise ValueError("weights and samples have different lengths")
    positive = int(np.count_nonzero(weights > 0.0))
    if positive == 0:
        raise ValueError("no positive nested weights")
    size = min(int(max_samples), positive)
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(weights), size=size, p=weights, replace=True)
    return samples[idx], idx, weights, ess


def run_dynesty(config: NestedRunConfig, loglike: Callable[[np.ndarray], float], *, pool_initializer=None,
                pool_initargs=()):
    """Run dynesty with delayed imports and return its results object."""
    config.validate()
    import dynesty
    from functools import partial
    from multiprocessing import get_context

    ptform = partial(prior_transform, bounds=config.bounds)
    ctx = get_context("spawn")
    with ctx.Pool(config.nproc, initializer=pool_initializer, initargs=pool_initargs) as pool:
        sampler = dynesty.NestedSampler(loglike, ptform, len(config.bounds), nlive=config.nlive,
                                        pool=pool, queue_size=config.nproc * 2)
        sampler.run_nested(dlogz=config.dlogz, print_progress=False, maxiter=config.maxiter)
    return sampler.results


def summarize_results(results, config: NestedRunConfig) -> dict:
    logz_raw = float(results.logz[-1])
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": config.kind,
        "nlive": int(config.nlive),
        "seed": int(config.seed),
        "resampling_method": RESAMPLING_METHOD,
        "logZ_raw": logz_raw,
        "logZ_correction": float(config.evidence_correction),
        "logZ": float(logz_raw + config.evidence_correction),
        "logZerr": float(results.logzerr[-1]),
        "ncall": int(np.asarray(results.ncall).sum()),
    }


def classify_samples(samples: np.ndarray, names: Sequence[str], classifier: Callable[[Mapping[str, float]], str]) -> tuple[dict, int]:
    labels = []
    for row in np.asarray(samples, dtype=float):
        label = classifier(dict(zip(names, map(float, row))))
        if label not in FATE_LABELS:
            raise ValueError(f"unknown fate label from classifier: {label!r}")
        labels.append(label)
    n = len(labels)
    if n == 0:
        raise ValueError("cannot classify zero samples")
    arr = np.array(labels)
    return {label: float((arr == label).mean()) for label in FATE_LABELS}, n


def add_resampling_audit(out: dict, *, weights: np.ndarray, ess: float, n_equal_weight: int) -> None:
    out.update({
        "n_samples": int(n_equal_weight),
        "n_equal_weight_samples": int(n_equal_weight),
        "n_weighted_samples": int(len(weights)),
        "ess": float(ess),
        "weight_sum": float(np.sum(weights)),
    })


def add_fate_summary(out: dict, probabilities: Mapping[str, float], n: int) -> None:
    p_rip = float(probabilities.get("RIP", 0.0))
    out["P_fate_nested"] = dict(probabilities)
    out["P_RIP_se_binom"] = float(np.sqrt(p_rip * (1.0 - p_rip) / n))
    out["uncertainty_note"] = UNCERTAINTY_NOTE


def atomic_write_json(path: str, payload: Mapping, *, indent: int = 1) -> None:
    parent = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(parent, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{os.path.basename(path)}.", suffix=".tmp", dir=parent, text=True)
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(payload, f, indent=indent)
            f.write("\n")
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        finally:
            raise
