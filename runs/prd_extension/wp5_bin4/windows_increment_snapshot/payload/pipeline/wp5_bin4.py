"""Perturbation-consistent smoothed BIN4 histories for CAMB DarkEnergyPPF.

WP5 keeps the registered redshift bins but represents each transition by the
prospectively frozen tanh kernel in x=ln(a).  CAMB receives a dense tabulated
w(a); it then evolves perturbations with its PPF dark-energy implementation.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

import numpy as np

from pipeline.wparams import Z_EDGES_BIN4


PRIMARY_DELTA_LNA = 0.01
SENSITIVITY_DELTAS = (0.005, 0.01, 0.02)
A_MIN = 1.0e-8
_TRANSITION_Z = np.asarray(Z_EDGES_BIN4[1:-1], dtype=float)
_TRANSITION_A_DESCENDING = 1.0 / (1.0 + _TRANSITION_Z)
# Ordered in increasing a: w4->w3, w3->w2, w2->w1.
TRANSITION_A = tuple(sorted(_TRANSITION_A_DESCENDING))


class WP5Bin4Error(ValueError):
    """Raised when a table would not represent the registered WP5 model."""


def _validate_values(w_values: Sequence[float], delta_lna: float) -> np.ndarray:
    values = np.asarray(w_values, dtype=np.float64)
    if values.shape != (4,) or np.any(~np.isfinite(values)):
        raise WP5Bin4Error("BIN4 requires four finite values ordered w1..w4")
    if np.any((values < -3.0) | (values > 1.0)):
        raise WP5Bin4Error("BIN4 values must remain inside [-3,1]")
    if not np.isfinite(delta_lna) or delta_lna <= 0:
        raise WP5Bin4Error("delta_lna must be positive and finite")
    return values


def smooth_bin4_w(a, w_values: Sequence[float], delta_lna: float = PRIMARY_DELTA_LNA):
    """Return the frozen tanh-smoothed four-bin history for positive ``a``.

    ``w_values`` is ordered by increasing redshift: ``(w1,w2,w3,w4)``.
    The low-a baseline is w4 and the three increasing-a transitions are
    w4->w3, w3->w2, and w2->w1.
    """
    values = _validate_values(w_values, delta_lna)
    scale = np.asarray(a, dtype=np.float64)
    if np.any(~np.isfinite(scale)) or np.any(scale <= 0):
        raise WP5Bin4Error("scale factors must be positive and finite")
    x = np.log(scale)
    ordered = values[::-1]  # w4,w3,w2,w1
    result = np.full_like(scale, ordered[0], dtype=np.float64)
    for edge, left, right in zip(TRANSITION_A, ordered[:-1], ordered[1:]):
        result += 0.5 * (right - left) * (
            1.0 + np.tanh((x - np.log(edge)) / delta_lna)
        )
    return float(result) if result.ndim == 0 else result


def make_w_table(
    w_of_a: Callable[[np.ndarray], np.ndarray],
    *,
    transition_a: Sequence[float] = (),
    delta_lna: float = PRIMARY_DELTA_LNA,
    a_min: float = A_MIN,
    base_points: int = 1200,
    points_per_transition: int = 240,
) -> tuple[np.ndarray, np.ndarray]:
    """Build a deterministic positive, increasing CAMB table ending at a=1."""
    if not 0 < a_min < 1 or base_points < 100 or points_per_transition < 20:
        raise WP5Bin4Error("invalid table-grid controls")
    x = list(np.linspace(np.log(a_min), 0.0, base_points))
    for edge in transition_a:
        if not a_min < edge < 1:
            raise WP5Bin4Error(f"transition outside table support: {edge}")
        half_width = 10.0 * delta_lna
        x.extend(np.linspace(np.log(edge) - half_width, np.log(edge) + half_width,
                             points_per_transition))
    x = np.unique(np.clip(np.asarray(x), np.log(a_min), 0.0))
    a = np.exp(x)
    a[-1] = 1.0
    w = np.asarray(w_of_a(a), dtype=np.float64)
    if w.shape != a.shape or np.any(~np.isfinite(w)):
        raise WP5Bin4Error("w(a) table is non-finite or has the wrong shape")
    return np.ascontiguousarray(a), np.ascontiguousarray(w)


def make_bin4_table(
    w1: float,
    w2: float,
    w3: float,
    w4: float,
    *,
    delta_lna: float = PRIMARY_DELTA_LNA,
    **grid_controls,
) -> tuple[np.ndarray, np.ndarray]:
    values = _validate_values((w1, w2, w3, w4), delta_lna)
    return make_w_table(
        lambda a: smooth_bin4_w(a, values, delta_lna),
        transition_a=TRANSITION_A,
        delta_lna=delta_lna,
        **grid_controls,
    )


def make_cpl_table(w0: float, wa: float, **grid_controls) -> tuple[np.ndarray, np.ndarray]:
    """Tabulate native CPL for WP5's machinery-reproduction gate."""
    if not np.isfinite(w0) or not np.isfinite(wa):
        raise WP5Bin4Error("CPL values must be finite")
    return make_w_table(lambda a: w0 + wa * (1.0 - a), **grid_controls)


def make_dark_energy_ppf(a: np.ndarray, w: np.ndarray, *, cs2: float = 1.0):
    """Construct CAMB's PPF model from an already audited table."""
    import camb.dark_energy

    model = camb.dark_energy.DarkEnergyPPF()
    model.cs2 = float(cs2)
    model.set_w_a_table(a, w)
    return model


def make_bin4_ppf(w1: float, w2: float, w3: float, w4: float, *,
                  delta_lna: float = PRIMARY_DELTA_LNA, **grid_controls):
    a, w = make_bin4_table(w1, w2, w3, w4, delta_lna=delta_lna, **grid_controls)
    return make_dark_energy_ppf(a, w)
