#!/usr/bin/env python3
"""Pre-inference audit for the registered WP4 full-CMB F0 reproduction.

This module deliberately stops before model construction or likelihood
evaluation.  It inventories the archived reference chains, external code, and
likelihood data needed by F0.  Sampling is not authorized until the separate
input-hash manifest has been generated and registered in ``data/MANIFEST.md``.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import platform
import sys
from importlib import metadata
from pathlib import Path

import numpy as np
import yaml


ROOT = Path(__file__).resolve().parents[1]
OFFICIAL_ROOT = ROOT / "runs" / "gate1" / "official"
WP4_ROOT = ROOT / "runs" / "prd_extension" / "wp4_full_cmb"
DEFAULT_OUTPUT = WP4_ROOT / "preflight.json"
DEFAULT_REFERENCE = WP4_ROOT / "official_reference.json"
INPUT_MANIFEST = WP4_ROOT / "input_manifest.json"
F0_CONFIG = ROOT / "pipeline" / "wp4_f0.yaml"
SMOKE_REPORT = WP4_ROOT / "smoke_test.json"
DATA_MANIFEST = ROOT / "data" / "MANIFEST.md"
PACKAGES_ROOT = ROOT / "data" / "cobaya_packages"

OFFICIAL_CHAIN_HASHES = {
    "chain.1.txt": "db81d299d59051ae5e1e8f67952320e08a1644a4a1f8d19267705aee32798877",
    "chain.2.txt": "442390266f6a3bfe88e9c7cd8e29d1e7cff47fc8582f3a3af80a6b40b9f83939",
    "chain.3.txt": "1c92edf523df34784633f6852f7564f3d953203ae939d5d2e8cd4c3fd6f580ae",
    "chain.4.txt": "b17dc02689c3a30dd34a96d91ac35180006f17d10b82331396ef55ce999594af",
}

REFERENCE_COLUMNS = {
    "w0": "w",
    "wa": "wa",
    "Omega_m": "omegam",
    "H0": "H0",
}

EXPECTED_OFFICIAL_LIKELIHOODS = (
    "desi_y3_cosmo_bindings.cobaya_likelihoods.bao_likelihoods_v1p2.desi_bao_all",
    "sn.pantheonplus",
    "planck_2018_lowl.TT_clik",
    "planck_2018_lowl.EE_clik",
    "planck_NPIPE_highl_CamSpec.TTTEEE",
    "act_dr6_lenslike_v1_2.ACTDR6LensLike",
)

REQUIRED_MODULES = {
    "clipy": "clipy",
    "act_dr6_lenslike": "act_dr6_lenslike",
}

REQUIRED_DISTRIBUTIONS = {
    "cobaya": "cobaya",
    "camb": "camb",
    "clipy-like": "clipy-like",
    "act-dr6-lenslike": "act-dr6-lenslike",
}

REQUIRED_DATA = {
    "desi_dr2_bao_mean": PACKAGES_ROOT
    / "data/bao_data/desi_bao_dr2/desi_gaussian_bao_ALL_GCcomb_mean.txt",
    "desi_dr2_bao_covariance": PACKAGES_ROOT
    / "data/bao_data/desi_bao_dr2/desi_gaussian_bao_ALL_GCcomb_cov.txt",
    "pantheonplus_dataset": PACKAGES_ROOT
    / "data/sn_data/PantheonPlus/config.dataset",
    "pantheonplus_catalogue": PACKAGES_ROOT
    / "data/sn_data/PantheonPlus/Pantheon+SH0ES.dat",
    "pantheonplus_covariance": PACKAGES_ROOT
    / "data/sn_data/PantheonPlus/Pantheon+SH0ES_STAT+SYS.cov",
    "planck_lowl_tt_clik": PACKAGES_ROOT
    / "data/planck_2018/baseline/plc_3.0/low_l/commander/"
    "commander_dx12_v3_2_29.clik",
    "planck_lowl_ee_clik": PACKAGES_ROOT
    / "data/planck_2018/baseline/plc_3.0/low_l/simall/"
    "simall_100x143_offlike5_EE_Aplanck_B.clik",
    "planck_supplementary_data": PACKAGES_ROOT
    / "data/planck_supp_data_and_covmats",
    "planck_npipe_camspec": PACKAGES_ROOT
    / "data/planck_NPIPE_CamSpec/CamSpec_NPIPE/"
    "CamSpec_NPIPE_12_6_cl.dataset",
    "act_dr6_lensing_v1p2": PACKAGES_ROOT / "data/ACT_dr6_likelihood/v1.2",
}

MANIFEST_MARKERS = (
    "## WP4 full-CMB F0",
    "`runs/prd_extension/wp4_full_cmb/input_manifest.json`",
    "clipy-like 0.15",
    "act-dr6-lenslike 1.2.1",
)


class WP4PreflightError(RuntimeError):
    """Raised when the archived F0 reference is malformed."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _chain_header(path: Path) -> list[str]:
    with path.open(encoding="utf-8") as stream:
        first = stream.readline().strip()
    if not first.startswith("#"):
        raise WP4PreflightError(f"missing chain header: {path}")
    return first[1:].split()


def official_reference(
    chain_paths: list[Path] | None = None,
    expected_hashes: dict[str, str] | None = None,
) -> dict:
    """Return deterministic weighted target moments from the official chains."""

    paths = chain_paths or [
        OFFICIAL_ROOT / name for name in sorted(OFFICIAL_CHAIN_HASHES)
    ]
    hashes = OFFICIAL_CHAIN_HASHES if expected_hashes is None else expected_hashes
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise WP4PreflightError(f"missing official chains: {missing}")

    chain_records = []
    weighted_sums = {name: 0.0 for name in REFERENCE_COLUMNS}
    weighted_squares = {name: 0.0 for name in REFERENCE_COLUMNS}
    total_weight = 0.0
    raw_rows = 0

    for path in paths:
        digest = sha256_file(path)
        expected = hashes.get(path.name)
        if expected is not None and digest != expected:
            raise WP4PreflightError(
                f"official chain hash mismatch for {path.name}: {digest} != {expected}"
            )
        header = _chain_header(path)
        required = ["weight", *REFERENCE_COLUMNS.values()]
        absent = [name for name in required if name not in header]
        if absent:
            raise WP4PreflightError(f"{path.name} lacks columns {absent}")
        usecols = [header.index(name) for name in required]
        values = np.loadtxt(path, comments="#", usecols=usecols, ndmin=2)
        weights = values[:, 0]
        if np.any(~np.isfinite(values)) or np.any(weights <= 0):
            raise WP4PreflightError(f"{path.name} contains invalid values or weights")
        chain_weight = float(np.sum(weights))
        total_weight += chain_weight
        raw_rows += int(values.shape[0])
        for offset, name in enumerate(REFERENCE_COLUMNS, start=1):
            column = values[:, offset]
            weighted_sums[name] += float(np.dot(weights, column))
            weighted_squares[name] += float(np.dot(weights, column * column))
        chain_records.append(
            {
                "file": display_path(path),
                "sha256": digest,
                "raw_rows": int(values.shape[0]),
                "posterior_weight": chain_weight,
            }
        )

    parameters = {}
    for name, source_column in REFERENCE_COLUMNS.items():
        mean = weighted_sums[name] / total_weight
        variance = max(weighted_squares[name] / total_weight - mean * mean, 0.0)
        parameters[name] = {
            "source_column": source_column,
            "mean": mean,
            "sd": variance**0.5,
        }

    return {
        "schema_version": "wp4-official-reference-v1",
        "source": (
            "DESI DR2 official flat-CPL chains: DESI BAO all + Pantheon+ + "
            "Planck low-l TT/EE + NPIPE CamSpec TTTEEE + Planck/ACT DR6 lensing"
        ),
        "chains": chain_records,
        "raw_rows": raw_rows,
        "posterior_weight": total_weight,
        "parameters": parameters,
        "gate_thresholds": {
            "max_mean_shift_pooled_sigma": 0.20,
            "max_sd_fractional_difference": 0.10,
            "max_abs_delta_chi2_difference": 1.0,
            "max_Rminus1": 0.01,
            "min_bulk_ess": 1000,
            "min_tail_ess_w0_wa": 400,
        },
    }


def _installed_versions() -> dict[str, str | None]:
    result = {}
    for label, distribution in REQUIRED_DISTRIBUTIONS.items():
        try:
            result[label] = metadata.version(distribution)
        except metadata.PackageNotFoundError:
            result[label] = None
    return result


def _official_config_audit() -> dict:
    path = OFFICIAL_ROOT / "chain.updated.yaml"
    if not path.is_file():
        return {"path": str(path.relative_to(ROOT)), "present": False}
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    likelihoods = tuple(config.get("likelihood", {}))
    return {
        "path": str(path.relative_to(ROOT)),
        "present": True,
        "sha256": sha256_file(path),
        "cobaya_version": str(config.get("version")),
        "camb_version": str(config.get("theory", {}).get("camb", {}).get("version")),
        "likelihoods": list(likelihoods),
        "likelihood_identity_match": likelihoods == EXPECTED_OFFICIAL_LIKELIHOODS,
        "free_parameters": [
            name
            for name, definition in config.get("params", {}).items()
            if isinstance(definition, dict) and "prior" in definition
        ],
    }


def audit_preflight() -> tuple[dict, dict]:
    reference = official_reference()
    config = _official_config_audit()
    module_status = {
        label: importlib.util.find_spec(module) is not None
        for label, module in REQUIRED_MODULES.items()
    }
    data_status = {
        label: {
            "path": str(path.relative_to(ROOT)),
            "present": path.exists(),
            "kind": "directory" if path.is_dir() else "file",
        }
        for label, path in REQUIRED_DATA.items()
    }
    versions = _installed_versions()
    manifest_text = (
        DATA_MANIFEST.read_text(encoding="utf-8") if DATA_MANIFEST.is_file() else ""
    )
    manifest_markers = {
        marker: marker in manifest_text for marker in MANIFEST_MARKERS
    }
    input_manifest_sha256 = (
        sha256_file(INPUT_MANIFEST) if INPUT_MANIFEST.is_file() else None
    )
    input_manifest_hash_registered = bool(
        input_manifest_sha256 and input_manifest_sha256 in manifest_text
    )
    smoke = (
        json.loads(SMOKE_REPORT.read_text(encoding="utf-8"))
        if SMOKE_REPORT.is_file()
        else None
    )
    smoke_passed = bool(
        smoke
        and smoke.get("status") == "PASS"
        and smoke.get("sampling_performed") is False
        and smoke.get("fate_calculation_performed") is False
        and smoke.get("config", {}).get("sha256")
        == (sha256_file(F0_CONFIG) if F0_CONFIG.is_file() else None)
        and smoke.get("input_manifest", {}).get("sha256")
        == input_manifest_sha256
    )

    missing_modules = [name for name, present in module_status.items() if not present]
    missing_distributions = [name for name, value in versions.items() if value is None]
    missing_data = [
        name for name, record in data_status.items() if not record["present"]
    ]
    provenance_ready = (
        INPUT_MANIFEST.is_file()
        and all(manifest_markers.values())
        and input_manifest_hash_registered
    )

    blockers = []
    if not config.get("likelihood_identity_match"):
        blockers.append("archived official likelihood identity mismatch")
    blockers.extend(f"missing module: {name}" for name in missing_modules)
    blockers.extend(
        f"missing distribution: {name}" for name in missing_distributions
    )
    blockers.extend(f"missing likelihood data: {name}" for name in missing_data)
    if not INPUT_MANIFEST.is_file():
        blockers.append("WP4 input_manifest.json has not been generated")
    elif not input_manifest_hash_registered:
        blockers.append("WP4 input manifest hash is not registered in data/MANIFEST.md")
    if not F0_CONFIG.is_file():
        blockers.append("portable WP4 F0 config is missing")
    for marker, present in manifest_markers.items():
        if not present:
            blockers.append(f"data/MANIFEST.md lacks marker: {marker}")

    if missing_modules or missing_distributions or missing_data:
        status = "BLOCKED_DEPENDENCIES"
        next_action = "install missing likelihood code/data and rerun this audit"
    elif not provenance_ready:
        status = "BLOCKED_PROVENANCE"
        next_action = (
            "generate the file-level input hash manifest and register it in "
            "data/MANIFEST.md before any likelihood evaluation"
        )
    elif blockers:
        status = "BLOCKED_CONFIGURATION"
        next_action = "resolve the remaining configuration blocker"
    elif smoke is not None and not smoke_passed:
        status = "BLOCKED_SMOKE"
        blockers.append("F0 smoke report is stale or failed")
        next_action = "rerun the no-sampling F0 smoke test"
    elif not smoke_passed:
        status = "READY_FOR_F0_SMOKE_TEST"
        next_action = (
            "run a no-sampling likelihood smoke test; do not calculate fate "
            "classifications during F0 reproduction"
        )
    else:
        status = "READY_FOR_F0_REPRODUCTION"
        next_action = (
            "derive and validate a proposal covariance, then launch F0 without "
            "calculating or inspecting fate classifications"
        )

    report = {
        "schema_version": "wp4-preflight-v1",
        "status": status,
        "inference_permitted": status == "READY_FOR_F0_REPRODUCTION",
        "fate_calculation_performed": False,
        "platform": {
            "python": sys.version.split()[0],
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "installed_versions": versions,
        "modules": module_status,
        "official_config": config,
        "official_reference": {
            "path": str(DEFAULT_REFERENCE.relative_to(ROOT)),
            "parameters": reference["parameters"],
        },
        "likelihood_data": data_status,
        "input_manifest": {
            "path": str(INPUT_MANIFEST.relative_to(ROOT)),
            "present": INPUT_MANIFEST.is_file(),
            "sha256": input_manifest_sha256,
            "hash_registered": input_manifest_hash_registered,
        },
        "f0_config": {
            "path": str(F0_CONFIG.relative_to(ROOT)),
            "present": F0_CONFIG.is_file(),
            "sha256": sha256_file(F0_CONFIG) if F0_CONFIG.is_file() else None,
        },
        "smoke_test": {
            "path": str(SMOKE_REPORT.relative_to(ROOT)),
            "present": SMOKE_REPORT.is_file(),
            "passed_and_current": smoke_passed,
        },
        "data_manifest_markers": manifest_markers,
        "blockers": blockers,
        "next_action": next_action,
    }
    return report, reference


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--reference-output", type=Path, default=DEFAULT_REFERENCE)
    args = parser.parse_args(argv)
    report, reference = audit_preflight()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.reference_output.write_text(
        json.dumps(reference, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"{report['status']}: wrote {args.output}")
    for blocker in report["blockers"]:
        print(f"- {blocker}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
