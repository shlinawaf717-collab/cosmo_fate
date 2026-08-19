#!/usr/bin/env python3
"""Mac development preflight for the WP5 tabulated-PPF BIN4 interface.

This is deliberately not the formal lmax=4000 WP5 gate.  It first separates
table/PPF machinery errors from the model difference introduced by smoothing
the registered piecewise history.
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import camb
import numpy as np
from camb import model
from scipy.integrate import cumulative_trapezoid

from pipeline.audit_wp4_f0_reproduction import atomic_write_json
from pipeline.wp5_bin4 import (
    make_bin4_table,
    make_cpl_table,
    make_dark_energy_ppf,
    smooth_bin4_w,
)
from pipeline.wparams import bin4_early_de_ratio


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "runs/prd_extension/wp5_bin4/development_preflight.json"
BACKGROUND_LIMIT = 1.0e-4
SPECTRUM_LIMIT = 1.0e-3
DESI_BAO_REDSHIFTS = (0.295, 0.510, 0.706, 0.934, 1.321, 1.484, 2.33)


def camb_params(kind: str, w0: float, wa: float):
    pars = camb.CAMBparams()
    pars.set_cosmology(H0=67.5, ombh2=0.02237, omch2=0.12, mnu=0.06,
                       nnu=3.044, num_massive_neutrinos=1, tau=0.0544)
    pars.InitPower.set_params(As=2.1e-9, ns=0.965)
    pars.set_for_lmax(1000, lens_potential_accuracy=1)
    pars.set_matter_power(redshifts=[0.0, 0.5, 1.0, 3.0], kmax=2.0)
    pars.NonLinear = model.NonLinear_none
    if kind == "native":
        pars.set_dark_energy(w=w0, wa=wa, dark_energy_model="ppf")
    elif kind == "table":
        a, w = make_cpl_table(w0, wa, base_points=1800)
        pars.DarkEnergy = make_dark_energy_ppf(a, w)
    else:
        raise ValueError(kind)
    return pars


def camb_products(pars):
    started = time.monotonic()
    results = camb.get_results(pars)
    spectra = results.get_cmb_power_spectra(
        pars, CMB_unit="muK", raw_cl=True
    )["total"]
    _, _, power = results.get_matter_power_spectrum(
        minkh=1.0e-3, maxkh=1.0, npoints=120
    )
    z = np.asarray([0.0, 0.1, 0.3, 0.7, 1.0, 2.0, 5.0, 10.0, 100.0, 1000.0])
    return {
        "runtime_seconds": time.monotonic() - started,
        "spectra": spectra,
        "power": power,
        "H": results.hubble_parameter(z),
        "chi": results.comoving_radial_distance(z),
    }


def compare_native_table(w0: float, wa: float) -> dict:
    native = camb_products(camb_params("native", w0, wa))
    table = camb_products(camb_params("table", w0, wa))
    result = {
        "w0": w0, "wa": wa,
        "runtime_seconds": [native["runtime_seconds"], table["runtime_seconds"]],
        "H_max_relative": float(np.max(np.abs(table["H"] / native["H"] - 1.0))),
        "chi_max_relative_nonzero": float(np.max(np.abs(table["chi"][1:] / native["chi"][1:] - 1.0))),
        "matter_power_max_relative": float(np.max(np.abs(table["power"] / native["power"] - 1.0))),
    }
    for index, name in ((0, "TT"), (1, "EE")):
        peak = max(float(np.max(np.abs(native["spectra"][:, index]))), 1e-300)
        result[f"{name}_max_absolute_over_reference_peak"] = float(
            np.max(np.abs(table["spectra"][:, index] - native["spectra"][:, index])) / peak
        )
    denominator = np.sqrt(np.maximum(
        np.abs(native["spectra"][:, 0] * native["spectra"][:, 1]), 1e-300
    ))
    result["TE_max_normalized"] = float(np.max(
        np.abs(table["spectra"][2:, 3] - native["spectra"][2:, 3]) / denominator[2:]
    ))
    result["background_pass"] = max(
        result["H_max_relative"], result["chi_max_relative_nonzero"]
    ) < BACKGROUND_LIMIT
    result["spectra_and_power_pass"] = max(
        result["TT_max_absolute_over_reference_peak"],
        result["EE_max_absolute_over_reference_peak"],
        result["TE_max_normalized"], result["matter_power_max_relative"],
    ) < SPECTRUM_LIMIT
    return result


def exact_piecewise_ln_fde(z: np.ndarray, values: np.ndarray) -> np.ndarray:
    z = np.asarray(z, dtype=float); result = np.zeros_like(z)
    finite_edges = (0.0, 0.3, 0.7, 1.5)
    for w, lo, hi in zip(values[:3], finite_edges[:-1], finite_edges[1:]):
        upper = np.minimum(z, hi)
        result += np.where(z > lo, 3.0 * (1.0 + w) * np.log((1.0 + upper) / (1.0 + lo)), 0.0)
    result += np.where(z > 1.5, 3.0 * (1.0 + values[3]) * np.log((1.0 + z) / 2.5), 0.0)
    return result


def compare_smooth_piecewise(name: str, values, *, omegam=0.3003901033,
                             H0=69.15309875) -> dict:
    values = np.asarray(values, dtype=float)
    u = np.linspace(0.0, np.log(1301.0), 200000)
    z = np.exp(u) - 1.0; a = np.exp(-u)
    exact_ln = exact_piecewise_ln_fde(z, values)
    h2 = (H0 / 100.0) ** 2
    omr = 2.4729e-5 * (1.0 + 0.2271 * 3.044) / h2
    ode = 1.0 - omegam - omr
    result = {"name": name, "w_values": list(map(float, values)), "omegam": omegam, "H0": H0,
              "early_de_ratio_z1059": bin4_early_de_ratio(omegam, H0, *values), "deltas": {}}
    for delta in (0.005, 0.01, 0.02):
        smooth_w = smooth_bin4_w(a, values, delta)
        smooth_ln = cumulative_trapezoid(3.0 * (1.0 + smooth_w), u, initial=0.0)
        exact_E = np.sqrt(omr * (1.0 + z) ** 4 + omegam * (1.0 + z) ** 3 + ode * np.exp(exact_ln))
        smooth_E = np.sqrt(omr * (1.0 + z) ** 4 + omegam * (1.0 + z) ** 3 + ode * np.exp(smooth_ln))
        exact_chi = cumulative_trapezoid(1.0 / exact_E, z, initial=0.0)
        smooth_chi = cumulative_trapezoid(1.0 / smooth_E, z, initial=0.0)
        mask = z > 1.0e-4
        H_error = float(np.max(np.abs(smooth_E / exact_E - 1.0)))
        chi_error = float(np.max(np.abs(smooth_chi[mask] / exact_chi[mask] - 1.0)))
        bao_H = np.interp(DESI_BAO_REDSHIFTS, z, smooth_E / exact_E - 1.0)
        bao_chi = np.interp(
            DESI_BAO_REDSHIFTS, z,
            smooth_chi / np.where(exact_chi == 0.0, 1.0, exact_chi) - 1.0,
        )
        result["deltas"][str(delta)] = {
            "ln_fde_max_absolute": float(np.max(np.abs(smooth_ln - exact_ln))),
            "H_max_relative": H_error, "chi_max_relative": chi_error,
            "DESI_BAO_redshifts": list(DESI_BAO_REDSHIFTS),
            "DESI_BAO_H_signed_relative": list(map(float, bao_H)),
            "DESI_BAO_chi_signed_relative": list(map(float, bao_chi)),
            "DESI_BAO_H_max_absolute_relative": float(np.max(np.abs(bao_H))),
            "formal_background_threshold": BACKGROUND_LIMIT,
            "formal_background_pass": max(H_error, chi_error) < BACKGROUND_LIMIT,
        }
    return result


def table_resolution_check(values, delta_lna=0.01) -> dict:
    products = []
    redshifts = np.unique(np.concatenate([
        np.linspace(0.0, 3.0, 600), np.asarray(DESI_BAO_REDSHIFTS),
        np.geomspace(3.01, 1300.0, 300),
    ]))
    for points in (1200, 3600):
        pars = camb.CAMBparams()
        pars.set_cosmology(H0=69.15309875, ombh2=0.02238049,
                           omch2=0.3003901033 * (69.15309875 / 100.0) ** 2
                           - 0.02238049 - 0.06 / 93.14,
                           mnu=0.06, nnu=3.044, num_massive_neutrinos=1)
        a, w = make_bin4_table(*values, delta_lna=delta_lna, base_points=points)
        pars.DarkEnergy = make_dark_energy_ppf(a, w)
        background = camb.get_background(pars)
        products.append({
            "base_points": points,
            "table_points": len(a),
            "H": background.hubble_parameter(redshifts),
            "chi": background.comoving_radial_distance(redshifts),
        })
    return {
        "coarse": {key: value for key, value in products[0].items() if key not in {"H", "chi"}},
        "fine": {key: value for key, value in products[1].items() if key not in {"H", "chi"}},
        "H_max_relative": float(np.max(np.abs(products[0]["H"] / products[1]["H"] - 1.0))),
        "chi_max_relative_nonzero": float(np.max(np.abs(
            products[0]["chi"][1:] / products[1]["chi"][1:] - 1.0
        ))),
    }


def run() -> dict:
    limits = [compare_native_table(-1.0, 0.0), compare_native_table(-0.9, 0.0),
              compare_native_table(-0.85, -0.6)]
    backgrounds = [
        compare_smooth_piecewise("mild_steps", (-0.9, -1.0, -1.1, -1.2)),
        compare_smooth_piecewise(
            "archived_compressed_BIN4_posterior_means",
            (-1.0001526733, -0.8898679517, -1.5257126119, -1.7125405922),
        ),
    ]
    resolution = table_resolution_check(
        (-1.0001526733, -0.8898679517, -1.5257126119, -1.7125405922)
    )
    interface_pass = all(row["background_pass"] and row["spectra_and_power_pass"] for row in limits)
    primary_piecewise_pass = all(
        row["deltas"]["0.01"]["formal_background_pass"] for row in backgrounds
    )
    return {
        "schema_version": "wp5-bin4-development-preflight-v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": ("READY_FOR_FORMAL_LMAX4000_GATE" if interface_pass and primary_piecewise_pass
                   else "BLOCKED_BEFORE_FORMAL_GATE"),
        "scope": "Mac reduced-lmax development diagnostic; no real-data fit and no WP5 scientific endpoint",
        "environment": {"camb": camb.__version__, "machine": "Mac arm64"},
        "thresholds": {"background_relative": BACKGROUND_LIMIT,
                       "spectra_and_matter_relative": SPECTRUM_LIMIT},
        "native_table_limit_checks": limits,
        "interface_limits_pass": interface_pass,
        "smooth_vs_exact_piecewise": backgrounds,
        "table_resolution_1200_vs_3600": resolution,
        "primary_delta_piecewise_background_pass": primary_piecewise_pass,
        "blocker_interpretation": (
            "The table/PPF machinery reproduces native limits. The current blocker is the finite "
            "difference between the registered tanh-smoothed model and the exact discontinuous-bin "
            "BackgroundW target near transitions; it is not repaired by increasing table resolution."
        ),
        "formal_no_go_declared": False,
        "next_action": "freeze an interpretation/correction decision before any full-likelihood BIN4 fit",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(); payload = run(); atomic_write_json(args.output, payload)
    print(json.dumps({"status": payload["status"], "output": str(args.output),
                      "interface_limits_pass": payload["interface_limits_pass"],
                      "primary_piecewise_background_pass": payload["primary_delta_piecewise_background_pass"]},
                     sort_keys=True))
    return 0


if __name__ == "__main__": raise SystemExit(main())
