"""Pure geometry and sampling helpers for the frozen WP8 continuation audit."""

from __future__ import annotations

import math
from typing import Iterable

import numpy as np
from scipy.interpolate import CubicSpline
from scipy.special import ndtr, ndtri

from pipeline.wp7_fs7 import ALL_X_NODES


TAUS = (0.5, 1.0, 2.0)
W_BOUNDS = (-3.0, 1.0)
GRID_SIZE = 512
GRID_X = np.linspace(0.0, math.log(1.0e6), GRID_SIZE, dtype=np.float64)
C3_DRAWS = 100_000
C3_LOC = -1.0
C3_SCALE = 0.5
C3_STANDARD_BOUNDS = (-4.0, 4.0)


class WP8GeometryError(ValueError):
    """Raised for an invalid WP8 continuation input."""


def _s1_response_weights() -> np.ndarray:
    """Linear response of the registered FS7 spline derivative at x=0."""

    columns = []
    for index in range(7):
        values = np.zeros(8, dtype=np.float64)
        values[index + 1] = 1.0
        curve = CubicSpline(
            ALL_X_NODES,
            values,
            bc_type=((1, 0.0), (1, 0.0)),
            extrapolate=False,
        )
        columns.append(float(curve(0.0, 1)))
    return np.asarray(columns, dtype=np.float64)


S1_RESPONSE_WEIGHTS = _s1_response_weights()


def boundary_derivative(nodes: np.ndarray) -> np.ndarray:
    """Return ``dw/dln(a)`` at ``a=1`` for one or more FS7 node rows."""

    values = np.asarray(nodes, dtype=np.float64)
    single = values.ndim == 1
    if single:
        values = values[None, :]
    if values.ndim != 2 or values.shape[1] != 7 or not np.all(np.isfinite(values)):
        raise WP8GeometryError("nodes must have shape (n,7) with finite values")
    result = (values + 1.0) @ S1_RESPONSE_WEIGHTS
    return result[0] if single else result


def continuation_values(
    w1: np.ndarray | float,
    s1: np.ndarray | float,
    w_inf: np.ndarray | float,
    tau: float,
    x: np.ndarray | float,
) -> np.ndarray:
    """Evaluate the registered smooth C2/C3 continuation."""

    tau = float(tau)
    if not math.isfinite(tau) or tau <= 0:
        raise WP8GeometryError("tau must be positive and finite")
    w1, s1, w_inf, x = np.broadcast_arrays(
        np.asarray(w1, dtype=np.float64),
        np.asarray(s1, dtype=np.float64),
        np.asarray(w_inf, dtype=np.float64),
        np.asarray(x, dtype=np.float64),
    )
    if np.any(~np.isfinite(w1)) or np.any(~np.isfinite(s1)) or np.any(~np.isfinite(w_inf)):
        raise WP8GeometryError("continuation state must be finite")
    if np.any(~np.isfinite(x)) or np.any(x < 0):
        raise WP8GeometryError("continuation coordinate must be finite and non-negative")
    a_term = w1 - w_inf
    b_term = s1 + a_term / tau
    return w_inf + (a_term + b_term * x) * np.exp(-x / tau)


def continuation_derivative(
    w1: np.ndarray | float,
    s1: np.ndarray | float,
    w_inf: np.ndarray | float,
    tau: float,
    x: np.ndarray | float,
) -> np.ndarray:
    """Return ``dw/dx`` for the registered smooth continuation."""

    tau = float(tau)
    w1, s1, w_inf, x = np.broadcast_arrays(
        np.asarray(w1, dtype=np.float64),
        np.asarray(s1, dtype=np.float64),
        np.asarray(w_inf, dtype=np.float64),
        np.asarray(x, dtype=np.float64),
    )
    a_term = w1 - w_inf
    b_term = s1 + a_term / tau
    return (b_term - (a_term + b_term * x) / tau) * np.exp(-x / tau)


def admissible_winf_interval(
    w1: np.ndarray,
    s1: np.ndarray,
    tau: float,
    *,
    grid_x: np.ndarray = GRID_X,
    bounds: tuple[float, float] = W_BOUNDS,
    chunk_size: int = 4096,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Intersect all affine grid constraints to obtain the complete support."""

    w1 = np.asarray(w1, dtype=np.float64)
    s1 = np.asarray(s1, dtype=np.float64)
    grid_x = np.asarray(grid_x, dtype=np.float64)
    if w1.ndim != 1 or s1.shape != w1.shape or not np.all(np.isfinite(w1 + s1)):
        raise WP8GeometryError("w1 and s1 must be finite one-dimensional peers")
    if grid_x.ndim != 1 or len(grid_x) < 2 or grid_x[0] != 0 or np.any(np.diff(grid_x) <= 0):
        raise WP8GeometryError("grid_x must start at zero and increase")
    lower_bound, upper_bound = map(float, bounds)
    if not lower_bound < upper_bound:
        raise WP8GeometryError("bounds must increase")
    tau = float(tau)
    if not math.isfinite(tau) or tau <= 0:
        raise WP8GeometryError("tau must be positive and finite")
    if int(chunk_size) != chunk_size or chunk_size < 1:
        raise WP8GeometryError("chunk_size must be a positive integer")

    x = grid_x[1:]
    u = x / tau
    exponential = np.exp(-u)
    beta = 1.0 - exponential * (1.0 + u)
    if np.any(beta <= 0):
        raise WP8GeometryError("non-positive affine coefficient beyond x=0")

    result_lower = np.empty(len(w1), dtype=np.float64)
    result_upper = np.empty(len(w1), dtype=np.float64)
    valid = np.empty(len(w1), dtype=bool)
    for start in range(0, len(w1), int(chunk_size)):
        stop = min(start + int(chunk_size), len(w1))
        alpha = exponential[None, :] * (
            w1[start:stop, None] * (1.0 + u[None, :])
            + s1[start:stop, None] * x[None, :]
        )
        low = np.maximum(lower_bound, np.max((lower_bound - alpha) / beta, axis=1))
        high = np.minimum(upper_bound, np.min((upper_bound - alpha) / beta, axis=1))
        at_boundary = (w1[start:stop] >= lower_bound) & (w1[start:stop] <= upper_bound)
        result_lower[start:stop] = low
        result_upper[start:stop] = high
        valid[start:stop] = at_boundary & (low <= high)
    return result_lower, result_upper, valid


def direct_admissible(
    w1: np.ndarray,
    s1: np.ndarray,
    w_inf: np.ndarray,
    tau: float,
    *,
    grid_x: np.ndarray = GRID_X,
    bounds: tuple[float, float] = W_BOUNDS,
    chunk_size: int = 4096,
) -> np.ndarray:
    """Direct registered-grid admissibility, primarily for validation."""

    w1, s1, w_inf = np.broadcast_arrays(
        np.asarray(w1, dtype=np.float64),
        np.asarray(s1, dtype=np.float64),
        np.asarray(w_inf, dtype=np.float64),
    )
    if w1.ndim != 1:
        raise WP8GeometryError("direct admissibility inputs must be one-dimensional")
    result = np.empty(len(w1), dtype=bool)
    low, high = map(float, bounds)
    for start in range(0, len(w1), int(chunk_size)):
        stop = min(start + int(chunk_size), len(w1))
        values = continuation_values(
            w1[start:stop, None],
            s1[start:stop, None],
            w_inf[start:stop, None],
            tau,
            np.asarray(grid_x)[None, :],
        )
        result[start:stop] = np.all((values >= low) & (values <= high), axis=1)
    return result


def systematic_weighted_indices(weights: np.ndarray, count: int) -> np.ndarray:
    """Deterministic inverse-weight empirical quantiles at midpoint positions."""

    weights = np.asarray(weights, dtype=np.float64)
    if weights.ndim != 1 or len(weights) == 0 or np.any(~np.isfinite(weights)) or np.any(weights <= 0):
        raise WP8GeometryError("weights must be a non-empty positive finite vector")
    if int(count) != count or count < 1:
        raise WP8GeometryError("count must be a positive integer")
    cumulative = np.cumsum(weights)
    targets = (np.arange(int(count), dtype=np.float64) + 0.5) * cumulative[-1] / count
    return np.searchsorted(cumulative, targets, side="left")


def c3_seed(tau: float, replicate: int) -> int:
    try:
        ordinal = TAUS.index(float(tau)) + 1
    except ValueError as exc:
        raise WP8GeometryError("tau is not registered") from exc
    if replicate not in (1, 2):
        raise WP8GeometryError("replicate must be 1 or 2")
    return 202607270800 + 10 * ordinal + int(replicate)


def draw_c3_asymptotes(count: int, seed: int) -> np.ndarray:
    """Inverse-CDF draws from the registered symmetric truncated Normal."""

    if int(count) != count or count < 1:
        raise WP8GeometryError("count must be a positive integer")
    cdf_low, cdf_high = ndtr(C3_STANDARD_BOUNDS)
    uniforms = np.random.Generator(np.random.PCG64(int(seed))).random(int(count))
    standard = ndtri(cdf_low + uniforms * (cdf_high - cdf_low))
    return C3_LOC + C3_SCALE * standard


def physical_fate(w_inf: np.ndarray) -> np.ndarray:
    """Finite-limit analytic WP8 fate labels."""

    values = np.asarray(w_inf, dtype=np.float64)
    if np.any(~np.isfinite(values)):
        raise WP8GeometryError("w_inf must be finite")
    labels = np.full(values.shape, "DS", dtype="U5")
    labels[values < -1.0] = "RIP"
    labels[values > -1.0] = "DECAY"
    return labels


def weighted_composition(labels: np.ndarray, weights: np.ndarray) -> dict:
    """Return physical fate fractions plus the heat/non-heat identities."""

    labels = np.asarray(labels)
    weights = np.asarray(weights, dtype=np.float64)
    if labels.shape != weights.shape or labels.ndim != 1 or np.any(weights <= 0):
        raise WP8GeometryError("labels and weights are incompatible")
    total = float(np.sum(weights))
    fractions = {
        name: float(np.sum(weights[labels == name]) / total)
        for name in ("RIP", "DS", "DECAY", "CRUNCH", "OTHER")
    }
    fractions["heat"] = fractions["DS"] + fractions["DECAY"]
    fractions["non_heat"] = fractions["RIP"] + fractions["CRUNCH"]
    return fractions


def bernoulli_mcse(probability: float, count: int) -> float:
    probability = float(probability)
    if not 0 <= probability <= 1 or int(count) != count or count < 1:
        raise WP8GeometryError("invalid Bernoulli MCSE input")
    return float(math.sqrt(probability * (1.0 - probability) / int(count)))


def support_categories(
    c0_winf: np.ndarray,
    c2_admissible: Iterable[np.ndarray],
    c3_intervals: Iterable[tuple[np.ndarray, np.ndarray, np.ndarray]],
) -> np.ndarray:
    """Union registered continuation sides into the v2 support-set category."""

    c0_winf = np.asarray(c0_winf, dtype=np.float64)
    if c0_winf.ndim != 1 or np.any(~np.isfinite(c0_winf)):
        raise WP8GeometryError("c0_winf must be a finite vector")
    rip = c0_winf < -1.0
    heat = c0_winf >= -1.0
    any_member = np.ones(len(c0_winf), dtype=bool)
    for admissible in c2_admissible:
        admissible = np.asarray(admissible, dtype=bool)
        if admissible.shape != c0_winf.shape:
            raise WP8GeometryError("C2 admissibility shape mismatch")
        heat |= admissible
        any_member |= admissible
    for lower, upper, valid in c3_intervals:
        lower = np.asarray(lower, dtype=np.float64)
        upper = np.asarray(upper, dtype=np.float64)
        valid = np.asarray(valid, dtype=bool)
        if lower.shape != c0_winf.shape or upper.shape != lower.shape or valid.shape != lower.shape:
            raise WP8GeometryError("C3 support shape mismatch")
        rip |= valid & (lower < -1.0)
        heat |= valid & (upper >= -1.0)
        any_member |= valid
    result = np.full(len(c0_winf), "empty/invalid", dtype="U16")
    result[any_member & rip & ~heat] = "{RIP}"
    result[any_member & heat & ~rip] = "{heat}"
    result[any_member & rip & heat] = "{RIP,heat}"
    return result
