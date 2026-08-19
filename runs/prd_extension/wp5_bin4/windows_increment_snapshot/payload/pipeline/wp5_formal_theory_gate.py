#!/usr/bin/env python3
"""Formal high-accuracy native-vs-tabulated theory limits for WP5."""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import camb
import numpy as np
from camb import model

from pipeline.audit_wp4_f0_reproduction import atomic_write_json
from pipeline.wp5_bin4 import make_cpl_table, make_dark_energy_ppf


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "runs/prd_extension/wp5_bin4/formal_theory_gate.json"
RELATIVE_LIMIT = 1.0e-3
BACKGROUND_LIMIT = 1.0e-4
LMAX = 4000


def build_params(kind: str, w0: float, wa: float):
    pars = camb.CAMBparams()
    pars.set_cosmology(
        H0=67.5, ombh2=0.02237, omch2=0.12, mnu=0.06, nnu=3.044,
        num_massive_neutrinos=1, tau=0.0544,
        bbn_predictor="PArthENoPE_880.2_standard.dat",
    )
    pars.InitPower.set_params(As=2.1e-9, ns=0.965)
    pars.set_for_lmax(LMAX, lens_potential_accuracy=4)
    pars.Accuracy.AccuracyBoost = 1
    pars.Accuracy.lSampleBoost = 1
    pars.Accuracy.lAccuracyBoost = 1
    pars.set_matter_power(redshifts=[0.0, 0.5, 1.0, 3.0], kmax=10.0)
    pars.NonLinear = model.NonLinear_both
    pars.NonLinearModel.set_params(halofit_version="mead2016")
    if kind == "native":
        pars.set_dark_energy(w=w0, wa=wa, dark_energy_model="ppf")
    elif kind == "table":
        a, w = make_cpl_table(w0, wa, base_points=3600)
        pars.DarkEnergy = make_dark_energy_ppf(a, w)
    else:
        raise ValueError(kind)
    return pars


def products(pars):
    started = time.monotonic()
    results = camb.get_results(pars)
    total = results.get_cmb_power_spectra(
        pars, CMB_unit="muK", raw_cl=True
    )["total"][: LMAX + 1]
    lens = results.get_lens_potential_cls(lmax=LMAX, raw_cl=True)
    kh, z, power = results.get_matter_power_spectrum(
        minkh=1.0e-3, maxkh=10.0, npoints=220
    )
    redshifts = np.asarray([0.0, 0.1, 0.3, 0.7, 1.0, 2.0, 5.0, 10.0, 100.0, 1000.0])
    return {
        "runtime_seconds": time.monotonic() - started,
        "total": total, "lens": lens, "kh": kh, "z": z, "power": power,
        "H": results.hubble_parameter(redshifts),
        "chi": results.comoving_radial_distance(redshifts),
    }


def max_relative(candidate: np.ndarray, reference: np.ndarray, *, start=0) -> float:
    candidate = np.asarray(candidate)[start:]
    reference = np.asarray(reference)[start:]
    if np.any(reference == 0):
        raise ValueError("relative comparison contains exact reference zero")
    return float(np.max(np.abs(candidate / reference - 1.0)))


def compare_case(name: str, w0: float, wa: float) -> dict:
    native = products(build_params("native", w0, wa))
    table = products(build_params("table", w0, wa))
    ell = slice(2, LMAX + 1)
    tt = max_relative(table["total"][:, 0], native["total"][:, 0], start=2)
    ee = max_relative(table["total"][:, 1], native["total"][:, 1], start=2)
    te_denominator = np.sqrt(np.maximum(
        np.abs(native["total"][ell, 0] * native["total"][ell, 1]), 1e-300
    ))
    te = float(np.max(np.abs(
        table["total"][ell, 3] - native["total"][ell, 3]
    ) / te_denominator))
    lens_pp = max_relative(table["lens"][:, 0], native["lens"][:, 0], start=2)
    matter = max_relative(table["power"], native["power"])
    H = max_relative(table["H"], native["H"])
    chi = max_relative(table["chi"], native["chi"], start=1)
    gates = {
        "H": H < BACKGROUND_LIMIT, "distance": chi < BACKGROUND_LIMIT,
        "TT": tt < RELATIVE_LIMIT, "EE": ee < RELATIVE_LIMIT,
        "TE": te < RELATIVE_LIMIT, "lensing_PP": lens_pp < RELATIVE_LIMIT,
        "matter_power": matter < RELATIVE_LIMIT,
    }
    return {
        "name": name, "w0": w0, "wa": wa,
        "runtime_seconds": {"native": native["runtime_seconds"], "table": table["runtime_seconds"]},
        "metrics": {"H_max_relative": H, "distance_max_relative": chi,
                    "TT_max_relative": tt, "EE_max_relative": ee,
                    "TE_max_sqrt_TT_EE_normalized": te,
                    "lensing_PP_max_relative": lens_pp,
                    "matter_power_max_relative": matter},
        "gates": gates, "status": "PASS" if all(gates.values()) else "FAIL",
    }


def run() -> dict:
    cases = [
        compare_case("LCDM", -1.0, 0.0),
        compare_case("constant_w", -0.9, 0.0),
        compare_case("CPL", -0.85, -0.6),
    ]
    return {
        "schema_version": "wp5-formal-theory-gate-v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if all(row["status"] == "PASS" for row in cases) else "FAIL",
        "scope": "no likelihood evaluation, posterior, fate endpoint, or real-data fit",
        "environment": {"camb": camb.__version__, "lmax": LMAX,
                        "lens_potential_accuracy": 4, "halofit": "mead2016"},
        "thresholds": {"background_relative": BACKGROUND_LIMIT,
                       "TT_EE_TE_lensing_matter_relative": RELATIVE_LIMIT},
        "cases": cases,
        "prerequisite": "PRD-A013 exact-smoothed background development gate PASS",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(); payload = run(); atomic_write_json(args.output, payload)
    print(json.dumps({"status": payload["status"], "output": str(args.output)}, sort_keys=True))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__": raise SystemExit(main())
