#!/usr/bin/env python3
"""Likelihood and independent-background fixed points for FS7 before sampling."""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from cobaya.model import get_model
from cobaya.yaml import yaml_load_file
from scipy.integrate import quad

from pipeline.audit_wp4_f0_reproduction import atomic_write_json
from pipeline.build_wp7_configs import ROOT, build
from pipeline.wp7_fs7 import (
    ALL_A_NODES,
    make_ln_fde as make_fs7_ln_fde,
    w_of_a as fs7_w_of_a,
)
from pipeline.wparams import make_ln_fde as make_generic_ln_fde


DEFAULT_OUTPUT = ROOT / "runs/prd_extension/wp7/fixed_point_preflight.json"
CHI2_LIMIT = 1.0e-8
BACKGROUND_LIMIT = 2.0e-5
POINT_COMMON = {"ombh2": 0.02236, "omegam": 0.30, "H0": 68.5, "Mb": -19.39}


def _model(info: dict):
    info = dict(info)
    info.pop("sampler", None)
    info.pop("output", None)
    info.pop("wp7_metadata", None)
    info["packages_path"] = str(ROOT / "data/cobaya_packages")
    return get_model(info)


def _loglikes(info: dict, point: dict) -> dict[str, float]:
    model = _model(info)
    try:
        posterior = model.logposterior(point, make_finite=False)
        return {name: float(value) for name, value in zip(model.likelihood, posterior.loglikes)}
    finally:
        model.close()


def run() -> dict:
    started = time.monotonic()
    fs7_info = build("primary")
    fs7_point = {**POINT_COMMON, **{f"z{i}": 0.0 for i in range(1, 8)}}
    fs7_likes = _loglikes(fs7_info, fs7_point)

    cpl_info = yaml_load_file(str(ROOT / "pipeline/fparam_base.yaml"))
    cpl_info["packages_path"] = str(ROOT / "data/cobaya_packages")
    cpl_point = {**POINT_COMMON, "w": -1.0, "wa": 0.0}
    cpl_likes = _loglikes(cpl_info, cpl_point)
    components = {}
    for name in fs7_likes:
        signed = -2.0 * (fs7_likes[name] - cpl_likes[name])
        components[name] = {
            "fs7_loglike": fs7_likes[name],
            "lcdm_cpl_loglike": cpl_likes[name],
            "signed_delta_chi2": signed,
            "pass": abs(signed) <= CHI2_LIMIT,
        }

    fixture = np.asarray([-0.90, -1.10, -0.85, -1.00, -1.20, -0.75, -1.05])
    generic = make_generic_ln_fde("fs7", {f"fs7_w{i}": value for i, value in enumerate(fixture, 1)})
    independent = make_fs7_ln_fde(fixture)
    scales = np.geomspace(1.0e-6, 1.0e4, 64)
    numeric = []
    for scale in scales:
        x = float(np.log(scale))
        lower, upper = sorted((0.0, x))
        value = quad(
            lambda xx: 3.0 * (1.0 + float(fs7_w_of_a(np.exp(xx), fixture))),
            lower,
            upper,
            epsabs=1e-11,
            epsrel=1e-11,
            limit=300,
            points=[point for point in np.log(ALL_A_NODES) if lower < point < upper],
        )[0]
        numeric.append(-value if x >= 0 else value)
    numeric = np.asarray(numeric)
    difference = float(max(
        np.max(np.abs(generic(scales) - numeric)),
        np.max(np.abs(independent(scales) - numeric)),
    ))
    gates = {
        "lcdm_component_chi2": all(row["pass"] for row in components.values()),
        "independent_background_integral": difference <= BACKGROUND_LIMIT,
    }
    return {
        "schema_version": "wp7-fs7-fixed-point-preflight-v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if all(gates.values()) else "FAIL",
        "thresholds": {"component_abs_delta_chi2": CHI2_LIMIT, "ln_fde_max_abs": BACKGROUND_LIMIT},
        "gates": gates,
        "lcdm_fixed_point": {"point": fs7_point, "components": components},
        "nontrivial_history_dual_path": {
            "nodes": fixture.tolist(),
            "grid_points": len(scales),
            "ln_fde_max_abs_difference": difference,
            "reference": "adaptive quadrature of 3(1+w) in ln(a)",
        },
        "development_correction": (
            "The first 4000-vs-5000 trapezoid comparison differed by "
            "5.488920624660554e-5 and failed the frozen 2e-5 gate. FS7 was "
            "therefore changed before sampling to the exact cubic-spline "
            "antiderivative; the threshold was not relaxed."
        ),
        "runtime_seconds": time.monotonic() - started,
        "scientific_role": "implementation identity only",
        "posterior_sampling_performed": False,
        "fate_endpoint_calculated": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    payload = run()
    atomic_write_json(args.output, payload)
    print(json.dumps({"status": payload["status"], "output": str(args.output)}, sort_keys=True))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
