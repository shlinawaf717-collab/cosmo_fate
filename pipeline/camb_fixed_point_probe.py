#!/usr/bin/env python3
"""Probe two CAMB versions at one official-chain fixed cosmology.

The probe is independent of the running WP4 F0 chains.  It extracts the
minimum-minuslogpost point from the already archived official chains, evaluates
CAMB geometry and spectra using the frozen WP4 accuracy settings, and writes
auditable JSON plus a compressed spectrum payload.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import camb
import numpy as np


SCHEMA_VERSION = "wp4-camb-fixed-point-probe-v1"
POINT_PARAMETERS = (
    "logA",
    "ns",
    "theta_MC_100",
    "ombh2",
    "omch2",
    "tau",
    "w",
    "wa",
)
DERIVED_PARAMETERS = (
    "age",
    "zstar",
    "rstar",
    "thetastar",
    "DAstar",
    "zdrag",
    "rdrag",
    "kd",
    "thetad",
    "zeq",
    "keq",
    "thetaeq",
    "thetarseq",
)
CAMB_SETTINGS = {
    "dark_energy_model": "ppf",
    "num_massive_neutrinos": 1,
    "halofit_version": "mead2016",
    "lmax": 4000,
    "lens_margin": 1250,
    "lens_potential_accuracy": 4,
    "AccuracyBoost": 1,
    "lSampleBoost": 1,
    "lAccuracyBoost": 1,
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_official_fixed_point(chain_paths: list[Path]) -> tuple[dict, dict]:
    best_values: dict[str, float] | None = None
    best_source: dict | None = None
    for path in chain_paths:
        with path.open("r", encoding="utf-8") as handle:
            header = handle.readline().lstrip("#").split()
        values = np.loadtxt(path, comments="#", ndmin=2)
        index = {name: i for i, name in enumerate(header)}
        missing = set(("minuslogpost", *POINT_PARAMETERS)).difference(index)
        if missing:
            raise ValueError(f"{path} lacks columns {sorted(missing)}")
        row_index = int(np.argmin(values[:, index["minuslogpost"]]))
        minuslogpost = float(values[row_index, index["minuslogpost"]])
        if best_values is None or minuslogpost < best_values["minuslogpost"]:
            best_values = {
                "minuslogpost": minuslogpost,
                **{
                    name: float(values[row_index, index[name]])
                    for name in POINT_PARAMETERS
                },
            }
            best_source = {
                "path": str(path),
                "sha256": sha256_file(path),
                "zero_based_data_row": row_index,
            }
    if best_values is None or best_source is None:
        raise ValueError("no official-chain samples found")
    return best_values, best_source


def _write_npz_atomic(path: Path, arrays: dict[str, np.ndarray]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(dir=path.parent, suffix=".npz")
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        np.savez_compressed(temporary, **arrays)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _write_json_atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        temporary = Path(handle.name)
    os.replace(temporary, path)


def run_probe(chain_paths: list[Path], json_path: Path, npz_path: Path) -> dict:
    point, source = load_official_fixed_point(chain_paths)
    started = time.monotonic()
    params = camb.set_params(
        cosmomc_theta=point["theta_MC_100"] / 100.0,
        ombh2=point["ombh2"],
        omch2=point["omch2"],
        tau=point["tau"],
        As=1e-10 * np.exp(point["logA"]),
        ns=point["ns"],
        w=point["w"],
        wa=point["wa"],
        **CAMB_SETTINGS,
    )
    results = camb.get_results(params)
    derived_raw = results.get_derived_params()
    spectra = results.get_cmb_power_spectra(
        params, CMB_unit="muK", raw_cl=True
    )
    arrays = {
        "total": np.asarray(spectra["total"], dtype=np.float64),
        "unlensed_scalar": np.asarray(
            spectra["unlensed_scalar"], dtype=np.float64
        ),
        "lens_potential": np.asarray(
            spectra["lens_potential"], dtype=np.float64
        ),
    }
    _write_npz_atomic(npz_path, arrays)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "non-authoritative CAMB version-drift screen",
        "running_f0_chain_data_read": False,
        "environment": {
            "camb": camb.__version__,
            "numpy": np.__version__,
            "python": platform.python_version(),
            "platform": platform.platform(),
            "omp_num_threads": os.environ.get("OMP_NUM_THREADS"),
        },
        "official_fixed_point": point,
        "official_fixed_point_source": source,
        "settings": CAMB_SETTINGS,
        "outputs": {
            "H0": float(params.H0),
            "omegam": float(results.get_Omega("baryon") + results.get_Omega("cdm")
                              + results.get_Omega("nu")),
            "omegal": float(results.get_Omega("de")),
            "derived": {
                name: float(derived_raw[name]) for name in DERIVED_PARAMETERS
            },
        },
        "spectra": {
            "path": str(npz_path),
            "sha256": sha256_file(npz_path),
            "arrays": {
                name: {"shape": list(array.shape), "dtype": str(array.dtype)}
                for name, array in arrays.items()
            },
        },
        "runtime_seconds": time.monotonic() - started,
    }
    _write_json_atomic(json_path, payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--chain",
        type=Path,
        action="append",
        dest="chains",
        help="official chain; repeat as needed",
    )
    parser.add_argument("--json", type=Path, required=True)
    parser.add_argument("--spectra-npz", type=Path, required=True)
    args = parser.parse_args()
    chains = args.chains or [
        Path(f"runs/gate1/official/chain.{index}.txt") for index in range(1, 5)
    ]
    payload = run_probe(chains, args.json, args.spectra_npz)
    print(
        json.dumps(
            {
                "camb": payload["environment"]["camb"],
                "json": str(args.json),
                "spectra_npz": str(args.spectra_npz),
                "runtime_seconds": payload["runtime_seconds"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
