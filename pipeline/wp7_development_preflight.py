#!/usr/bin/env python3
"""Deterministic implementation preflight for WP7 FS7 before inference."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from pipeline.wp7_fs7 import (
    ALL_A_NODES,
    FREE_A_NODES,
    admissibility,
    conditional_future_geometry,
    covariance,
    latent_to_nodes,
    make_ln_fde,
    nodes_to_latent,
    spline,
    w_of_a,
)


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "plan/prd_extension_protocol.json"
ANALYTIC = ROOT / "plan/wp7_analytic_prediction.json"
DEFAULT_OUTPUT = ROOT / "runs/prd_extension/wp7_development/preflight.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build() -> dict:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))["wp7_fs7"]
    settings = [protocol["primary_hyperparameters"], *protocol["sensitivity_hyperparameters"]]
    fixture = np.asarray([0.20, -0.15, 0.10, -0.05, 0.08, -0.04, 0.02])
    records = []
    for setting in settings:
        sigma_f, ell = float(setting["sigma_f"]), float(setting["ell"])
        cov = covariance(sigma_f, ell)
        nodes = latent_to_nodes(fixture, sigma_f, ell)
        recovered = nodes_to_latent(nodes, sigma_f, ell)
        geometry = conditional_future_geometry(sigma_f, ell)
        records.append({
            "sigma_f": sigma_f,
            "ell": ell,
            "minimum_eigenvalue": float(np.linalg.eigvalsh(cov)[0]),
            "condition_number": float(np.linalg.cond(cov)),
            "latent_roundtrip_max_abs_error": float(np.max(np.abs(recovered - fixture))),
            "fixture_admissibility": admissibility(nodes).__dict__,
            "a4_conditional_sd_given_nodes_a_le_1": geometry["conditional_sd"],
            "a4_multiple_R2_from_nodes_a_le_1": geometry["multiple_R2"],
        })

    lcdm_nodes = np.full(7, -1.0)
    curve = spline(lcdm_nodes)
    knot_error = float(np.max(np.abs(w_of_a(ALL_A_NODES, lcdm_nodes) + 1.0)))
    derivative_error = float(
        max(abs(curve.derivative()(np.log(ALL_A_NODES[0]))), abs(curve.derivative()(np.log(ALL_A_NODES[-1]))))
    )
    probes = np.geomspace(1.0e-6, 1.0e4, 1000)
    extension_error = float(np.max(np.abs(w_of_a(probes, lcdm_nodes) + 1.0)))
    density_error = float(np.max(np.abs(make_ln_fde(lcdm_nodes)(probes))))
    checks = {
        "registered_nodes_match": np.allclose(FREE_A_NODES, protocol["free_a_nodes"], rtol=0, atol=1e-15),
        "lcdm_knot_identity": knot_error < 1e-14,
        "clamped_endpoint_derivatives": derivative_error < 1e-13,
        "constant_extensions": extension_error < 1e-14,
        "lcdm_density_identity": density_error < 1e-13,
        "zero_latent_admissible": admissibility(latent_to_nodes(np.zeros(7), 0.5, 0.7)).admissible,
        "all_roundtrips_stable": all(row["latent_roundtrip_max_abs_error"] < 1e-8 for row in records),
    }
    return {
        "schema_version": "wp7-fs7-development-preflight-v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS_WITH_ELL_1P4_WARNING" if all(checks.values()) else "FAIL",
        "inputs": {
            "protocol": {"path": str(PROTOCOL.relative_to(ROOT)), "sha256": sha256(PROTOCOL)},
            "analytic_prediction": {"path": str(ANALYTIC.relative_to(ROOT)), "sha256": sha256(ANALYTIC)},
        },
        "checks": checks,
        "implementation_identities": {
            "lcdm_knot_max_abs_error": knot_error,
            "endpoint_derivative_max_abs_error": derivative_error,
            "constant_extension_max_abs_error": extension_error,
            "lcdm_ln_fde_max_abs_error": density_error,
        },
        "hyperparameter_geometry": records,
        "prior_simulation_performed": False,
        "likelihood_evaluation_performed": False,
        "posterior_sampling_performed": False,
        "fate_endpoint_calculated": False,
        "next_gate": "implement normalized truncation workflow and D0 no-sampling smoke",
    }


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as stream:
        json.dump(payload, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
        temporary = Path(stream.name)
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    payload = build()
    atomic_json(args.output, payload)
    print(json.dumps({"status": payload["status"], "output": str(args.output)}, sort_keys=True))
    return 0 if payload["status"].startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
