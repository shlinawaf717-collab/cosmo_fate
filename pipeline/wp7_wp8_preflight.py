#!/usr/bin/env python3
"""Analytic and numerical preflight for the frozen WP7/WP8 designs.

This script uses only protocol priors and deterministic probe states.  It does
not read WP7/WP8 posterior samples or calculate a scientific endpoint.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.interpolate import CubicSpline


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "plan/prd_extension_protocol.json"
WP8_V1 = ROOT / "plan/wp8_future_continuation_protocol.json"
DEFAULT_OUTPUT = (
    ROOT / "runs/prd_extension/wp7_wp8_preflight/preflight.json"
)
SCHEMA_VERSION = "wp7-wp8-analytic-numerical-preflight-v1"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def admissible_winf_interval(
    w1: float,
    s1: float,
    tau: float,
    *,
    points: int = 512,
    a_max: float = 1e6,
    w_bounds: tuple[float, float] = (-3.0, 1.0),
) -> tuple[float, float] | None:
    """Return the grid-exact C3 asymptote interval allowed by function bounds.

    At fixed ``(w1,s1,tau)``, the registered continuation is affine in
    ``w_inf``.  Each grid bound therefore contributes one linear interval;
    their intersection is the complete registered admissible support.
    """
    x = np.linspace(0.0, np.log(a_max), points)
    decay = np.exp(-x / tau)
    alpha = 1.0 - (1.0 + x / tau) * decay
    beta = (w1 + (s1 + w1 / tau) * x) * decay
    if not w_bounds[0] <= w1 <= w_bounds[1]:
        return None
    lower, upper = map(float, w_bounds)
    for coefficient, offset in zip(alpha[1:], beta[1:]):
        point_lower = (w_bounds[0] - offset) / coefficient
        point_upper = (w_bounds[1] - offset) / coefficient
        lower = max(lower, float(min(point_lower, point_upper)))
        upper = min(upper, float(max(point_lower, point_upper)))
        if lower > upper:
            return None
    return lower, upper


def _wp7_covariance_preflight(spec: dict) -> list[dict]:
    nodes = np.log(np.asarray(spec["free_a_nodes"], dtype=np.float64))
    observed = np.flatnonzero(np.asarray(spec["free_a_nodes"]) <= 1.0)
    settings = [
        spec["primary_hyperparameters"],
        *spec["sensitivity_hyperparameters"],
    ]
    records = []
    for setting in settings:
        sigma = float(setting["sigma_f"])
        ell = float(setting["ell"])
        delta = nodes[:, None] - nodes[None, :]
        covariance = sigma**2 * np.exp(-0.5 * delta**2 / ell**2)
        covariance += float(spec["jitter"]) * np.eye(nodes.size)
        eigenvalues = np.linalg.eigvalsh(covariance)
        cholesky = np.linalg.cholesky(covariance)
        reconstructed = cholesky @ cholesky.T
        relative_residual = float(
            np.linalg.norm(reconstructed - covariance, ord=np.inf)
            / np.linalg.norm(covariance, ord=np.inf)
        )
        solve_residual = float(
            np.linalg.norm(
                covariance @ np.linalg.solve(covariance, np.eye(nodes.size))
                - np.eye(nodes.size),
                ord=np.inf,
            )
        )
        future_index = nodes.size - 1
        c_oo = covariance[np.ix_(observed, observed)]
        c_fo = covariance[future_index, observed]
        conditional_variance = float(
            covariance[future_index, future_index]
            - c_fo @ np.linalg.solve(c_oo, covariance[observed, future_index])
        )
        multiple_r2 = float(
            1.0
            - conditional_variance / covariance[future_index, future_index]
        )
        condition_number = float(eigenvalues[-1] / eigenvalues[0])
        records.append(
            {
                "sigma_f": sigma,
                "ell": ell,
                "minimum_eigenvalue": float(eigenvalues[0]),
                "maximum_eigenvalue": float(eigenvalues[-1]),
                "condition_number": condition_number,
                "cholesky_relative_infinity_residual": relative_residual,
                "inverse_solve_infinity_residual": solve_residual,
                "a4_conditional_sd_given_nodes_a_le_1": float(
                    np.sqrt(conditional_variance)
                ),
                "a4_multiple_R2_from_nodes_a_le_1": multiple_r2,
                "numerical_status": (
                    "WARN_HIGH_CONDITION_NUMBER"
                    if condition_number >= 1e8
                    else "PASS"
                ),
            }
        )
    return records


def _spline_leakage_preflight(spec: dict) -> dict:
    all_a = np.asarray(
        [spec["fixed_early_anchor"]["a"], *spec["free_a_nodes"]],
        dtype=np.float64,
    )
    all_x = np.log(all_a)
    observed_a = np.geomspace(0.25, 1.0, 512)
    observed_x = np.log(observed_a)
    responses = []
    for index, node_a in enumerate(all_a):
        if node_a <= 1.0:
            continue
        basis = np.zeros(all_a.size)
        basis[index] = 1.0
        spline = CubicSpline(
            all_x,
            basis,
            bc_type=((1, 0.0), (1, 0.0)),
        )
        response = spline(observed_x)
        maximum_index = int(np.argmax(np.abs(response)))
        responses.append(
            {
                "future_node_a": float(node_a),
                "max_abs_response_over_a_le_1": float(
                    np.max(np.abs(response))
                ),
                "a_at_max_abs_response": float(observed_a[maximum_index]),
                "response_at_a1": float(spline(0.0)),
            }
        )
    maximum = max(
        row["max_abs_response_over_a_le_1"] for row in responses
    )
    return {
        "definition": (
            "unit future-node basis response of the registered global "
            "clamped cubic spline over a in [0.25,1]"
        ),
        "responses": responses,
        "maximum_abs_response": maximum,
        "status": "PAST_FUTURE_COUPLING_DETECTED" if maximum > 1e-12 else "PASS",
        "interpretation": (
            "future-node posterior shifts cannot be called direct future-data "
            "constraints without reporting this deterministic spline coupling"
        ),
    }


def _wp8_structural_preflight(spec: dict) -> dict:
    tau_values = next(
        family["tau_values"]
        for family in spec["families"]
        if family["id"] == "C3"
    )
    probes = []
    for w1 in (-1.1, -1.0, -0.9):
        for s1 in (-0.2, 0.0, 0.2):
            for tau in tau_values:
                interval = admissible_winf_interval(w1, s1, tau)
                probes.append(
                    {
                        "w1": w1,
                        "s1": s1,
                        "tau": tau,
                        "admissible_winf_interval": (
                            list(interval) if interval is not None else None
                        ),
                        "support_crosses_fate_boundary": (
                            interval is not None
                            and interval[0] < -1.0 < interval[1]
                        ),
                    }
                )
    return {
        "C2_fate": {
            "w_inf": -1.0,
            "fate": "DS",
            "P_RIP": 0.0,
            "tau_changes_fate": False,
            "tau_can_change_admissibility": True,
        },
        "C3_unconditioned_asymptote_measure": {
            "distribution": "symmetric truncated Normal(-1,0.5^2) on [-3,1]",
            "P_RIP": 0.5,
            "P_heat": 0.5,
            "likelihood_information": 0.0,
        },
        "admissibility_warning": (
            "conditioning on path admissibility can reweight w_inf through "
            "(w1,s1,tau); that selection-conditioned composition is not a "
            "likelihood posterior update of the independent asymptote measure"
        ),
        "registered_grid_probe_states": probes,
        "all_probe_intervals_cross_boundary": all(
            row["support_crosses_fate_boundary"] for row in probes
        ),
        "robust_fraction_disposition": (
            "replace the v1 thresholded robust fraction with an analytic "
            "partial-identification support-set statement"
        ),
    }


def build_preflight() -> dict:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    wp8 = json.loads(WP8_V1.read_text(encoding="utf-8"))
    wp7 = protocol["wp7_fs7"]
    covariance = _wp7_covariance_preflight(wp7)
    spline = _spline_leakage_preflight(wp7)
    structural = _wp8_structural_preflight(wp8)
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "wp7_protocol": {
                "path": str(PROTOCOL.relative_to(ROOT)),
                "sha256": _sha256(PROTOCOL),
            },
            "wp8_v1_protocol": {
                "path": str(WP8_V1.relative_to(ROOT)),
                "sha256": _sha256(WP8_V1),
            },
        },
        "posterior_or_scientific_endpoint_read": False,
        "wp7_covariance": covariance,
        "wp7_spline_past_future_leakage": spline,
        "wp8_structural_controls": structural,
        "status": "PASS_WITH_DECLARED_STRUCTURAL_WARNINGS",
        "production_disposition": {
            "change_wp7_jitter_before_sampling": False,
            "retain_ell_1p4_with_warning_and_convergence_gate": True,
            "retain_global_spline_as_registered_model": True,
            "require_leakage_caveat_and_decomposition": True,
            "apply_wp8_v2_partial_identification_amendment": True,
        },
    }


def _atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
        temporary = Path(handle.name)
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = build_preflight()
    _atomic_json(args.output, report)
    print(
        json.dumps(
            {
                "status": report["status"],
                "output": str(args.output),
                "ell_1p4_condition_number": next(
                    row["condition_number"]
                    for row in report["wp7_covariance"]
                    if row["ell"] == 1.4
                ),
                "maximum_spline_leakage": report[
                    "wp7_spline_past_future_leakage"
                ]["maximum_abs_response"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
