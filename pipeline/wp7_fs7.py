"""Pure implementation of the frozen WP7 FS7 function-space model.

This module contains geometry and prior-coordinate operations only. It does
not read chains, evaluate the cosmological likelihood, or classify a
scientific fate endpoint.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import log, pi
from typing import Sequence

import numpy as np
from scipy.interpolate import CubicSpline


EARLY_ANCHOR_A = 0.25
EARLY_ANCHOR_W = -1.0
FREE_A_NODES = np.asarray(
    [0.40, 1.0 / 1.7, 1.0 / 1.3, 1.0, 1.50, 2.00, 4.00],
    dtype=np.float64,
)
ALL_A_NODES = np.concatenate([[EARLY_ANCHOR_A], FREE_A_NODES])
ALL_X_NODES = np.log(ALL_A_NODES)
NODE_BOUNDS = (-3.0, 1.0)
JITTER = 1.0e-10
FUNCTION_GRID_SIZE = 512


class FS7Error(ValueError):
    """Raised when an FS7 coordinate or hyperparameter is invalid."""


def _vector(values: Sequence[float], *, name: str, size: int = 7) -> np.ndarray:
    result = np.asarray(values, dtype=np.float64)
    if result.shape != (size,) or not np.all(np.isfinite(result)):
        raise FS7Error(f"{name} must contain {size} finite values")
    return result


def covariance(sigma_f: float, ell: float, *, jitter: float = JITTER) -> np.ndarray:
    """Return the registered squared-exponential covariance at free nodes."""
    sigma_f, ell, jitter = float(sigma_f), float(ell), float(jitter)
    if not np.isfinite(sigma_f) or sigma_f <= 0:
        raise FS7Error("sigma_f must be positive and finite")
    if not np.isfinite(ell) or ell <= 0:
        raise FS7Error("ell must be positive and finite")
    if not np.isfinite(jitter) or jitter < 0:
        raise FS7Error("jitter must be non-negative and finite")
    x = np.log(FREE_A_NODES)
    delta = x[:, None] - x[None, :]
    return sigma_f**2 * np.exp(-0.5 * delta**2 / ell**2) + jitter * np.eye(7)


def cholesky(sigma_f: float, ell: float, *, jitter: float = JITTER) -> np.ndarray:
    """Cholesky factor used by the registered non-centred parameterization."""
    return np.linalg.cholesky(covariance(sigma_f, ell, jitter=jitter))


def latent_to_nodes(
    latent: Sequence[float], sigma_f: float, ell: float, *, jitter: float = JITTER
) -> np.ndarray:
    """Map standard-normal latent coordinates to the seven free ``w`` nodes."""
    z = _vector(latent, name="latent")
    return -1.0 + cholesky(sigma_f, ell, jitter=jitter) @ z


def nodes_to_latent(
    nodes: Sequence[float], sigma_f: float, ell: float, *, jitter: float = JITTER
) -> np.ndarray:
    """Inverse non-centred map, used only for validation and diagnostics."""
    w = _vector(nodes, name="nodes")
    return np.linalg.solve(cholesky(sigma_f, ell, jitter=jitter), w + 1.0)


def spline(nodes: Sequence[float]) -> CubicSpline:
    """Return the unique registered global clamped spline in ``ln(a)``."""
    w = _vector(nodes, name="nodes")
    values = np.concatenate([[EARLY_ANCHOR_W], w])
    return CubicSpline(
        ALL_X_NODES,
        values,
        bc_type=((1, 0.0), (1, 0.0)),
        extrapolate=False,
    )


def w_of_a(a: float | np.ndarray, nodes: Sequence[float]) -> float | np.ndarray:
    """Evaluate the frozen FS7 history, including both constant extensions."""
    scale = np.asarray(a, dtype=np.float64)
    if np.any(~np.isfinite(scale)) or np.any(scale <= 0):
        raise FS7Error("scale factor must be positive and finite")
    w = _vector(nodes, name="nodes")
    result = np.empty_like(scale)
    early = scale <= EARLY_ANCHOR_A
    future = scale >= FREE_A_NODES[-1]
    middle = ~(early | future)
    result[early] = EARLY_ANCHOR_W
    result[future] = w[-1]
    if np.any(middle):
        result[middle] = spline(w)(np.log(scale[middle]))
    return float(result) if result.ndim == 0 else result


def function_grid(size: int = FUNCTION_GRID_SIZE) -> np.ndarray:
    if int(size) != size or size < 2:
        raise FS7Error("function grid size must be an integer >= 2")
    return np.geomspace(EARLY_ANCHOR_A, FREE_A_NODES[-1], int(size))


def spline_response_matrix(a: Sequence[float]) -> np.ndarray:
    """Linear response of ``w(a)+1`` to the seven node residuals."""
    scale = np.asarray(a, dtype=np.float64)
    if scale.ndim != 1:
        raise FS7Error("response grid must be one-dimensional")
    columns = []
    for index in range(7):
        nodes = np.full(7, -1.0)
        nodes[index] = 0.0
        columns.append(np.asarray(w_of_a(scale, nodes)) + 1.0)
    return np.column_stack(columns)


def admissible_latent_mask(
    latent: np.ndarray,
    sigma_f: float,
    ell: float,
    *,
    grid_size: int = FUNCTION_GRID_SIZE,
) -> np.ndarray:
    """Vectorized registered truncation indicator for prior calibration."""
    z = np.asarray(latent, dtype=np.float64)
    if z.ndim != 2 or z.shape[1] != 7 or not np.all(np.isfinite(z)):
        raise FS7Error("latent batch must have shape (n,7) with finite values")
    residuals = z @ cholesky(sigma_f, ell).T
    node_ok = np.all((residuals >= -2.0) & (residuals <= 2.0), axis=1)
    response = spline_response_matrix(function_grid(grid_size))
    result = np.zeros(z.shape[0], dtype=bool)
    if np.any(node_ok):
        paths = residuals[node_ok] @ response.T
        result[node_ok] = np.all((paths >= -2.0) & (paths <= 2.0), axis=1)
    return result


@dataclass(frozen=True)
class Admissibility:
    admissible: bool
    nodes_within_bounds: bool
    spline_within_bounds: bool
    minimum_w: float
    maximum_w: float
    grid_size: int


def admissibility(
    nodes: Sequence[float],
    *,
    bounds: tuple[float, float] = NODE_BOUNDS,
    grid_size: int = FUNCTION_GRID_SIZE,
) -> Admissibility:
    """Apply the registered node and 512-point spline-overshoot bounds."""
    w = _vector(nodes, name="nodes")
    lower, upper = map(float, bounds)
    if not lower < upper:
        raise FS7Error("bounds must be increasing")
    node_ok = bool(np.all((w >= lower) & (w <= upper)))
    values = np.asarray(w_of_a(function_grid(grid_size), w), dtype=np.float64)
    spline_ok = bool(np.all((values >= lower) & (values <= upper)))
    return Admissibility(
        admissible=node_ok and spline_ok,
        nodes_within_bounds=node_ok,
        spline_within_bounds=spline_ok,
        minimum_w=float(np.min(values)),
        maximum_w=float(np.max(values)),
        grid_size=int(grid_size),
    )


def log_unnormalized_truncated_latent_prior(
    latent: Sequence[float], sigma_f: float, ell: float
) -> float:
    """Log density in latent coordinates, excluding the truncation constant.

    The omitted constant depends on the fixed hyperparameter setting. It
    cancels in within-setting posterior MCMC but must be estimated before any
    evidence or cross-setting normalized-density calculation. WP7 forbids
    using this function for Bayes factors without that additional validation.
    """
    z = _vector(latent, name="latent")
    if not admissibility(latent_to_nodes(z, sigma_f, ell)).admissible:
        return -np.inf
    return float(-0.5 * z @ z - 0.5 * z.size * log(2.0 * pi))


def _external_admissibility(
    z1, z2, z3, z4, z5, z6, z7, *, sigma_f: float, ell: float
) -> float:
    """Cobaya external-prior indicator in non-centred coordinates."""
    nodes = latent_to_nodes((z1, z2, z3, z4, z5, z6, z7), sigma_f, ell)
    return 0.0 if admissibility(nodes).admissible else -np.inf


def admissibility_primary(z1, z2, z3, z4, z5, z6, z7):
    return _external_admissibility(z1, z2, z3, z4, z5, z6, z7, sigma_f=0.5, ell=0.7)


def admissibility_sig025(z1, z2, z3, z4, z5, z6, z7):
    return _external_admissibility(z1, z2, z3, z4, z5, z6, z7, sigma_f=0.25, ell=0.7)


def admissibility_sig100(z1, z2, z3, z4, z5, z6, z7):
    return _external_admissibility(z1, z2, z3, z4, z5, z6, z7, sigma_f=1.0, ell=0.7)


def admissibility_ell035(z1, z2, z3, z4, z5, z6, z7):
    return _external_admissibility(z1, z2, z3, z4, z5, z6, z7, sigma_f=0.5, ell=0.35)


def admissibility_ell140(z1, z2, z3, z4, z5, z6, z7):
    return _external_admissibility(z1, z2, z3, z4, z5, z6, z7, sigma_f=0.5, ell=1.4)


def conditional_future_geometry(
    sigma_f: float, ell: float, *, jitter: float = JITTER
) -> dict:
    """Prior geometry of the ``a=4`` residual given free nodes at ``a<=1``."""
    cov = covariance(sigma_f, ell, jitter=jitter)
    observed = np.flatnonzero(FREE_A_NODES <= 1.0)
    future = len(FREE_A_NODES) - 1
    c_oo = cov[np.ix_(observed, observed)]
    c_fo = cov[future, observed]
    weights = np.linalg.solve(c_oo, cov[observed, future])
    variance = float(cov[future, future] - c_fo @ weights)
    return {
        "observed_indices": observed.tolist(),
        "conditional_mean_weights": weights.tolist(),
        "conditional_variance": variance,
        "conditional_sd": float(np.sqrt(variance)),
        "multiple_R2": float(1.0 - variance / cov[future, future]),
    }


def make_ln_fde(nodes: Sequence[float], *, grid_size: int = 5000):
    """Return ``ln[rho_DE(a)/rho_DE(1)]`` for background-only D0 work."""
    if grid_size < 100:
        raise FS7Error("background integration grid is too small")
    w = _vector(nodes, name="nodes")
    a_grid = np.geomspace(1.0e-9, 1.0e5, int(grid_size))
    x_grid = np.log(a_grid)
    integrand = 3.0 * (1.0 + np.asarray(w_of_a(a_grid, w)))
    cumulative = np.concatenate(
        [[0.0], np.cumsum(0.5 * (integrand[1:] + integrand[:-1]) * np.diff(x_grid))]
    )
    at_one = np.interp(0.0, x_grid, cumulative)
    values = -(cumulative - at_one)

    def ln_fde(a):
        scale = np.asarray(a, dtype=np.float64)
        result = np.interp(np.log(scale), x_grid, values)
        return float(result) if result.ndim == 0 else result

    ln_fde.grid = (a_grid, values)
    return ln_fde
