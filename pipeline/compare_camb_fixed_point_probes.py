#!/usr/bin/env python3
"""Compare two versioned outputs from camb_fixed_point_probe.py."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


SCHEMA_VERSION = "wp4-camb-fixed-point-comparison-v1"
# Frozen before the first version comparison.  This is a drift screen, not the
# WP4 posterior/likelihood equivalence decision.
SCREEN_THRESHOLDS = {
    "H0_absolute": 0.01,
    "rdrag_absolute": 0.01,
    "thetastar_absolute": 1e-4,
    "spectrum_rms_over_reference_rms": 5e-4,
    "spectrum_max_abs_over_reference_peak": 2e-3,
}
SPECTRUM_COLUMNS = {
    "total": ("TT", "EE", "BB", "TE"),
    "unlensed_scalar": ("TT", "EE", "BB", "TE"),
    "lens_potential": ("PP", "PT", "PE"),
}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json_atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        temporary = Path(handle.name)
    os.replace(temporary, path)


def compare_probes(
    reference_json: Path,
    candidate_json: Path,
    reference_npz: Path,
    candidate_npz: Path,
) -> dict:
    reference = _load(reference_json)
    candidate = _load(candidate_json)
    if reference["official_fixed_point"] != candidate["official_fixed_point"]:
        raise ValueError("fixed points differ")
    if reference["settings"] != candidate["settings"]:
        raise ValueError("CAMB settings differ")
    geometry = {}
    for name, reference_value, candidate_value in (
        ("H0", reference["outputs"]["H0"], candidate["outputs"]["H0"]),
        (
            "rdrag",
            reference["outputs"]["derived"]["rdrag"],
            candidate["outputs"]["derived"]["rdrag"],
        ),
        (
            "thetastar",
            reference["outputs"]["derived"]["thetastar"],
            candidate["outputs"]["derived"]["thetastar"],
        ),
    ):
        difference = float(candidate_value - reference_value)
        geometry[name] = {
            "absolute_difference": abs(difference),
            "signed_difference": difference,
            "relative_difference": (
                difference / reference_value if reference_value else None
            ),
        }
    reference_arrays = np.load(reference_npz)
    candidate_arrays = np.load(candidate_npz)
    spectra = {}
    spectrum_passes = []
    for array_name, column_names in SPECTRUM_COLUMNS.items():
        reference_array = reference_arrays[array_name]
        candidate_array = candidate_arrays[array_name]
        if reference_array.shape != candidate_array.shape:
            raise ValueError(f"shape differs for {array_name}")
        for column_index, column_name in enumerate(column_names):
            # Exclude monopole and dipole, which are not analysis multipoles.
            reference_column = reference_array[2:, column_index]
            candidate_column = candidate_array[2:, column_index]
            delta = candidate_column - reference_column
            reference_rms = float(np.sqrt(np.mean(reference_column**2)))
            reference_peak = float(np.max(np.abs(reference_column)))
            delta_rms = float(np.sqrt(np.mean(delta**2)))
            delta_peak = float(np.max(np.abs(delta)))
            rms_ratio = (
                delta_rms / reference_rms
                if reference_rms
                else (0.0 if delta_rms == 0.0 else float("inf"))
            )
            max_ratio = (
                delta_peak / reference_peak
                if reference_peak
                else (0.0 if delta_peak == 0.0 else float("inf"))
            )
            key = f"{array_name}.{column_name}"
            passes = (
                rms_ratio
                < SCREEN_THRESHOLDS["spectrum_rms_over_reference_rms"]
                and max_ratio
                < SCREEN_THRESHOLDS["spectrum_max_abs_over_reference_peak"]
            )
            spectra[key] = {
                "rms_over_reference_rms": rms_ratio,
                "max_abs_over_reference_peak": max_ratio,
                "pass": passes,
            }
            spectrum_passes.append(passes)
    gates = {
        "H0": geometry["H0"]["absolute_difference"]
        < SCREEN_THRESHOLDS["H0_absolute"],
        "rdrag": geometry["rdrag"]["absolute_difference"]
        < SCREEN_THRESHOLDS["rdrag_absolute"],
        "thetastar": geometry["thetastar"]["absolute_difference"]
        < SCREEN_THRESHOLDS["thetastar_absolute"],
        "spectra": all(spectrum_passes),
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "non-authoritative CAMB version-drift screen",
        "scope_warning": (
            "Passing does not establish full-likelihood or posterior equivalence "
            "and cannot stop or validate the running F0 chains."
        ),
        "reference": {
            "json": str(reference_json),
            "camb": reference["environment"]["camb"],
        },
        "candidate": {
            "json": str(candidate_json),
            "camb": candidate["environment"]["camb"],
        },
        "thresholds_frozen_before_comparison": SCREEN_THRESHOLDS,
        "geometry": geometry,
        "spectra": spectra,
        "gates": gates,
        "status": "PASS" if all(gates.values()) else "INVESTIGATE",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference-json", type=Path, required=True)
    parser.add_argument("--candidate-json", type=Path, required=True)
    parser.add_argument("--reference-npz", type=Path, required=True)
    parser.add_argument("--candidate-npz", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = compare_probes(
        args.reference_json,
        args.candidate_json,
        args.reference_npz,
        args.candidate_npz,
    )
    _write_json_atomic(args.output, payload)
    print(json.dumps({"status": payload["status"], "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
