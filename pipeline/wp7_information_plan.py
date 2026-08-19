#!/usr/bin/env python3
"""Freeze prior-quantile KL bins and likelihood-window response for WP7."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from pipeline.audit_wp4_f0_reproduction import atomic_write_json
from pipeline.build_wp7_configs import ROOT, SETTINGS
from pipeline.wp7_fs7 import (
    cholesky,
    conditional_future_geometry,
    draw_truncated_latents,
    spline_response_matrix,
)
from pipeline.wp7_sbc import FS7MockBackground, common_assets, dataset_assets


DEFAULT_OUTPUT = ROOT / "runs/prd_extension/wp7/information_plan.json"
PRIOR_DRAWS = 200_000
BIN_COUNTS = (20, 40, 80)


def _quantile_edges(values: np.ndarray, bins: int) -> list[float]:
    edges = np.quantile(values, np.linspace(0.0, 1.0, bins + 1))
    if np.any(np.diff(edges) <= 0):
        raise RuntimeError("prior quantile edges are not strictly increasing")
    return edges.tolist()


def _prior_records() -> dict:
    records = {}
    for ordinal, (tag, (sigma, ell, _)) in enumerate(SETTINGS.items(), 1):
        seed = 2026130000 + ordinal
        latent, rejection = draw_truncated_latents(
            PRIOR_DRAWS, sigma, ell, seed=seed, batch_size=32768
        )
        nodes = -1.0 + latent @ cholesky(sigma, ell).T
        geometry = conditional_future_geometry(sigma, ell)
        observed = geometry["observed_indices"]
        weights = np.asarray(geometry["conditional_mean_weights"])
        residual = (nodes[:, -1] + 1.0) - (nodes[:, observed] + 1.0) @ weights
        variables = {f"fs7_w{i}": nodes[:, i - 1] for i in range(1, 8)}
        variables["a4_conditional_residual"] = residual
        records[tag] = {
            "sigma_f": sigma,
            "ell": ell,
            "seed": seed,
            "draws": PRIOR_DRAWS,
            "rejection_audit": rejection,
            "conditional_future_geometry": geometry,
            "quantile_edges": {
                name: {str(bins): _quantile_edges(values, bins) for bins in BIN_COUNTS}
                for name, values in variables.items()
            },
            "fate_composition_calculated": False,
        }
    return records


def _prediction_vector(truth: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    background = FS7MockBackground(truth)
    assets = dataset_assets(truth, background)
    return (
        np.asarray(assets["sn_mu"])[assets["sn_mask"]],
        np.asarray(assets["bao_mu"]),
        np.asarray(assets["cmb_mu"]),
    )


def _likelihood_window_response() -> dict:
    common = common_assets()
    base = {
        "H0": 68.5,
        "omegam": 0.30,
        "ombh2": 0.02236,
        "Mb": -19.39,
        "fs7_nodes": [-1.0] * 7,
    }
    epsilon = 1.0e-3
    responses = []
    for node_index in (5, 6, 7):
        plus, minus = dict(base), dict(base)
        plus["fs7_nodes"] = list(base["fs7_nodes"])
        minus["fs7_nodes"] = list(base["fs7_nodes"])
        plus["fs7_nodes"][node_index - 1] += epsilon
        minus["fs7_nodes"][node_index - 1] -= epsilon
        derivatives = [
            (high - low) / (2.0 * epsilon)
            for high, low in zip(_prediction_vector(plus), _prediction_vector(minus))
        ]
        whitened = {
            "SN": float(np.linalg.norm(np.linalg.solve(common["L_sn"], derivatives[0])) ** 2),
            "BAO": float(np.linalg.norm(np.linalg.solve(common["L_bao"], derivatives[1])) ** 2),
            "CMB_distance_prior": float(np.linalg.norm(np.linalg.solve(common["L_cmb"], derivatives[2])) ** 2),
        }
        responses.append({
            "future_node": f"fs7_w{node_index}",
            "a": [1.5, 2.0, 4.0][node_index - 5],
            "finite_difference_epsilon": epsilon,
            "local_whitened_response_squared": whitened,
            "total_local_whitened_response_squared": float(sum(whitened.values())),
        })
    observed_grid = np.geomspace(0.25, 1.0, 512)
    basis = spline_response_matrix(observed_grid)
    return {
        "reference_point": base,
        "future_node_responses": responses,
        "spline_basis_max_abs_over_a_le_1": {
            f"fs7_w{index}": float(np.max(np.abs(basis[:, index - 1])))
            for index in (5, 6, 7)
        },
        "interpretation": "local likelihood pathway caused by the registered global spline, not observation of a>1",
    }


def build() -> dict:
    return {
        "schema_version": "wp7-fs7-information-plan-v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "FROZEN_BEFORE_WP7_POSTERIOR",
        "estimator": {
            "primary_bins": 40,
            "sensitivity_bins": [20, 80],
            "definition": "weighted posterior histogram in equal-prior-mass bins; sum p log(p/q), q=1/bins",
            "zero_bin_rule": "zero posterior mass contributes zero; no pseudocount",
        },
        "prior_reference": _prior_records(),
        "likelihood_window_response": _likelihood_window_response(),
        "posterior_or_fate_endpoint_read": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if args.output.is_file():
        raise RuntimeError("refusing to overwrite frozen WP7 information plan")
    payload = build()
    atomic_write_json(args.output, payload)
    print(json.dumps({"status": payload["status"], "output": str(args.output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
