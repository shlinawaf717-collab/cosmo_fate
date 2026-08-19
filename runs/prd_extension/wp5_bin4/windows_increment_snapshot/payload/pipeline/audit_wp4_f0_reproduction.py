#!/usr/bin/env python3
"""Unblinded WP4 F0 reproduction audit against the archived DESI DR2 products.

This audit is intentionally separate from the blinded convergence monitor.  It
may run only after ``final_stop_audit.json`` records a successful external
stop.  It compares post-burn F0 marginal moments with the official chains and
compares the local CPL-vs-LCDM optimized likelihood difference with the
official posterior-maximization products when both local minima exist.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
WP4_ROOT = ROOT / "runs" / "prd_extension" / "wp4_full_cmb"
F0_ROOT = WP4_ROOT / "f0"
FINAL_STOP_AUDIT = F0_ROOT / "external_monitor" / "final_stop_audit.json"
OFFICIAL_REFERENCE = WP4_ROOT / "official_reference.json"
DEFAULT_OUTPUT = WP4_ROOT / "f0_reproduction_audit.json"
LOCAL_BESTFIT_ROOT = WP4_ROOT / "f0_bestfits"
OFFICIAL_BESTFIT_ROOT = ROOT / "runs" / "gate1" / "official_bestfits"
ROW_BURN_FRACTION = 0.5
PARAMETERS = {
    "w0": "w",
    "wa": "wa",
    "Omega_m": "omegam",
    "H0": "H0",
}
OFFICIAL_BESTFIT_URLS = {
    "cpl": (
        "https://data.desi.lbl.gov/public/papers/y3/bao-cosmo-params/iminuit/"
        "base_w_wa/desi-bao-all_pantheonplus_planck2018-lowl-TT-clik_"
        "planck2018-lowl-EE-clik_planck-NPIPE-highl-CamSpec-TTTEEE_"
        "planck-act-dr6-lensing/bestfit.minimum.txt"
    ),
    "lcdm": (
        "https://data.desi.lbl.gov/public/papers/y3/bao-cosmo-params/iminuit/"
        "base/desi-bao-all_pantheonplus_planck2018-lowl-TT-clik_"
        "planck2018-lowl-EE-clik_planck-NPIPE-highl-CamSpec-TTTEEE_"
        "planck-act-dr6-lensing/bestfit.minimum.txt"
    ),
}


class WP4ReproductionError(RuntimeError):
    """Raised when a frozen input or an audit invariant is violated."""


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


def _header(path: Path) -> list[str]:
    with path.open(encoding="utf-8") as stream:
        line = stream.readline().strip()
    if not line.startswith("#"):
        raise WP4ReproductionError(f"missing table header: {path}")
    return line[1:].split()


def weighted_moments(
    paths: list[Path],
    columns: dict[str, str] = PARAMETERS,
    burn_fraction: float = ROW_BURN_FRACTION,
) -> tuple[dict, list[dict]]:
    """Compute deterministic integer-weighted population moments."""

    if not 0 <= burn_fraction < 1:
        raise WP4ReproductionError("burn fraction must lie in [0,1)")
    sums = {name: 0.0 for name in columns}
    sums2 = {name: 0.0 for name in columns}
    total_weight = 0.0
    records = []
    for path in paths:
        if not path.is_file():
            raise WP4ReproductionError(f"missing chain: {path}")
        header = _header(path)
        required = ["weight", *columns.values()]
        missing = [name for name in required if name not in header]
        if missing:
            raise WP4ReproductionError(f"{path} lacks columns {missing}")
        usecols = [header.index(name) for name in required]
        data = np.loadtxt(path, comments="#", usecols=usecols, ndmin=2)
        full_rows = int(data.shape[0])
        first = int(full_rows * burn_fraction)
        selected = data[first:]
        if not selected.size or np.any(~np.isfinite(selected)):
            raise WP4ReproductionError(f"invalid post-burn data: {path}")
        weights = selected[:, 0]
        if np.any(weights <= 0) or np.any(weights != np.floor(weights)):
            raise WP4ReproductionError(f"non-positive or non-integer weights: {path}")
        chain_weight = float(weights.sum())
        total_weight += chain_weight
        for offset, name in enumerate(columns, 1):
            values = selected[:, offset]
            sums[name] += float(np.dot(weights, values))
            sums2[name] += float(np.dot(weights, values * values))
        records.append(
            {
                "path": display_path(path),
                "sha256": sha256_file(path),
                "full_rows": full_rows,
                "post_burn_rows": int(selected.shape[0]),
                "post_burn_weight": int(chain_weight),
            }
        )
    if total_weight <= 0:
        raise WP4ReproductionError("zero total posterior weight")
    moments = {}
    for name in columns:
        mean = sums[name] / total_weight
        variance = max(sums2[name] / total_weight - mean * mean, 0.0)
        moments[name] = {"mean": mean, "sd": variance**0.5}
    return moments, records


def compare_moments(local: dict, official: dict, thresholds: dict) -> dict:
    rows = {}
    for name in PARAMETERS:
        local_mean = float(local[name]["mean"])
        local_sd = float(local[name]["sd"])
        official_mean = float(official[name]["mean"])
        official_sd = float(official[name]["sd"])
        pooled_sd = ((local_sd**2 + official_sd**2) / 2) ** 0.5
        mean_shift = abs(local_mean - official_mean) / pooled_sd
        sd_fractional_difference = abs(local_sd - official_sd) / official_sd
        rows[name] = {
            "source_column": PARAMETERS[name],
            "local_mean": local_mean,
            "official_mean": official_mean,
            "local_sd": local_sd,
            "official_sd": official_sd,
            "pooled_sd": pooled_sd,
            "absolute_mean_difference": abs(local_mean - official_mean),
            "mean_shift_pooled_sd": mean_shift,
            "mean_gate_pass": mean_shift
            <= float(thresholds["max_mean_shift_pooled_sigma"]),
            "sd_fractional_difference_vs_official": sd_fractional_difference,
            "sd_gate_pass": sd_fractional_difference
            <= float(thresholds["max_sd_fractional_difference"]),
        }
    return {
        "parameters": rows,
        "all_mean_gates_pass": all(row["mean_gate_pass"] for row in rows.values()),
        "all_sd_gates_pass": all(row["sd_gate_pass"] for row in rows.values()),
        "max_mean_shift_pooled_sd": max(
            row["mean_shift_pooled_sd"] for row in rows.values()
        ),
        "max_sd_fractional_difference_vs_official": max(
            row["sd_fractional_difference_vs_official"] for row in rows.values()
        ),
    }


def parse_one_point(path: Path) -> dict[str, float]:
    header = _header(path)
    data = np.loadtxt(path, comments="#", ndmin=2)
    if data.shape != (1, len(header)):
        raise WP4ReproductionError(
            f"expected one row and {len(header)} columns in {path}, got {data.shape}"
        )
    if np.any(~np.isfinite(data)):
        raise WP4ReproductionError(f"non-finite best-fit values: {path}")
    return {name: float(value) for name, value in zip(header, data[0])}


def atomic_likelihood_chi2(row: dict[str, float]) -> tuple[float, dict[str, float]]:
    """Return the sum of non-aggregated likelihood-component chi-squares."""

    aggregate_names = {"chi2__BAO", "chi2__CMB", "chi2__SN"}
    components = {
        name: value
        for name, value in row.items()
        if name.startswith("chi2__") and name not in aggregate_names
    }
    if not components:
        if "chi2" not in row:
            raise WP4ReproductionError("best-fit row lacks likelihood chi-square")
        return float(row["chi2"]), {}
    return float(sum(components.values())), components


def delta_chi2_audit(
    official_paths: dict[str, Path],
    local_paths: dict[str, Path],
    threshold: float,
) -> dict:
    official = {model: parse_one_point(path) for model, path in official_paths.items()}
    official_chi2 = {
        model: atomic_likelihood_chi2(row) for model, row in official.items()
    }
    official_delta = official_chi2["cpl"][0] - official_chi2["lcdm"][0]
    official_records = {
        model: {
            "path": display_path(path),
            "url": OFFICIAL_BESTFIT_URLS[model],
            "sha256": sha256_file(path),
            "reported_total_chi2": row["chi2"],
            "atomic_component_sum_chi2": official_chi2[model][0],
            "atomic_components": official_chi2[model][1],
            "minuslogpost": row["minuslogpost"],
            "minuslogprior": row["minuslogprior"],
        }
        for (model, path), row in zip(official_paths.items(), official.values())
    }
    missing = [display_path(path) for path in local_paths.values() if not path.is_file()]
    base = {
        "definition": (
            "CPL chi2 minus LCDM chi2, evaluated at each model's posterior "
            "maximum and summed from non-aggregated likelihood components; "
            "negative values favor CPL"
        ),
        "official": {
            "models": official_records,
            "delta_chi2_cpl_minus_lcdm": official_delta,
        },
        "threshold_max_absolute_difference": float(threshold),
        "numeric_resolution_note": (
            "Comparison uses the decimal precision published in each "
            "bestfit.minimum.txt component; the 1.0 gate is much wider than "
            "the resulting rounding scale."
        ),
    }
    if missing:
        return {**base, "status": "PENDING_LOCAL_OPTIMIZATION", "missing": missing}
    local = {model: parse_one_point(path) for model, path in local_paths.items()}
    local_chi2 = {model: atomic_likelihood_chi2(row) for model, row in local.items()}
    local_delta = local_chi2["cpl"][0] - local_chi2["lcdm"][0]
    difference = abs(local_delta - official_delta)
    local_records = {
        model: {
            "path": display_path(path),
            "sha256": sha256_file(path),
            "reported_total_chi2": row["chi2"],
            "atomic_component_sum_chi2": local_chi2[model][0],
            "atomic_components": local_chi2[model][1],
            "minuslogpost": row["minuslogpost"],
            "minuslogprior": row["minuslogprior"],
        }
        for (model, path), row in zip(local_paths.items(), local.values())
    }
    return {
        **base,
        "status": "PASS" if difference <= threshold else "FAIL",
        "local": {
            "models": local_records,
            "delta_chi2_cpl_minus_lcdm": local_delta,
        },
        "absolute_delta_chi2_difference": difference,
        "gate_pass": difference <= threshold,
    }


def audit() -> dict:
    final = json.loads(FINAL_STOP_AUDIT.read_text(encoding="utf-8"))
    if final.get("status") != "EXTERNALLY_STOPPED":
        raise WP4ReproductionError("F0 has not been externally stopped")
    if final.get("post_termination_gates_pass") is not True:
        raise WP4ReproductionError("F0 post-termination convergence audit did not pass")
    final_snapshots = final["post_termination_diagnostics"]["chain_snapshots"]
    chain_paths = [Path(record["path"]) for record in final_snapshots]
    for path, frozen in zip(chain_paths, final_snapshots):
        if sha256_file(path) != frozen["sha256"]:
            raise WP4ReproductionError(f"finalized chain hash changed: {path}")

    local_moments, chain_records = weighted_moments(chain_paths)
    official_reference = json.loads(OFFICIAL_REFERENCE.read_text(encoding="utf-8"))
    thresholds = official_reference["gate_thresholds"]
    comparison = compare_moments(
        local_moments, official_reference["parameters"], thresholds
    )
    delta = delta_chi2_audit(
        {
            "cpl": OFFICIAL_BESTFIT_ROOT / "base_w_wa" / "bestfit.minimum.txt",
            "lcdm": OFFICIAL_BESTFIT_ROOT / "base" / "bestfit.minimum.txt",
        },
        {
            "cpl": LOCAL_BESTFIT_ROOT / "cpl" / "bestfit.minimum.txt",
            "lcdm": LOCAL_BESTFIT_ROOT / "lcdm" / "bestfit.minimum.txt",
        },
        float(thresholds["max_abs_delta_chi2_difference"]),
    )
    convergence_pass = bool(final["post_termination_gates_pass"])
    moments_pass = bool(
        comparison["all_mean_gates_pass"] and comparison["all_sd_gates_pass"]
    )
    if delta["status"] == "PENDING_LOCAL_OPTIMIZATION":
        status = "PENDING_DELTA_CHI2"
    else:
        status = (
            "PASS"
            if convergence_pass and moments_pass and delta.get("gate_pass") is True
            else "FAIL"
        )
    return {
        "schema_version": "wp4-f0-reproduction-audit-v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "unblinding": {
            "authorized_by": "user instruction in Codex task",
            "precondition": "successful frozen F0 external-stop audit",
            "final_stop_audit": display_path(FINAL_STOP_AUDIT),
            "final_stop_audit_sha256": sha256_file(FINAL_STOP_AUDIT),
            "precondition_pass": True,
            "fate_quantities_computed": False,
        },
        "posterior_moments": {
            "status": "PASS" if moments_pass else "FAIL",
            "estimator": "integer-weighted population mean and SD",
            "f0_row_burn_fraction_per_chain": ROW_BURN_FRACTION,
            "official_row_burn_fraction": 0.0,
            "f0_chains": chain_records,
            "f0_post_burn_weight": sum(
                record["post_burn_weight"] for record in chain_records
            ),
            "official_reference": display_path(OFFICIAL_REFERENCE),
            "official_reference_sha256": sha256_file(OFFICIAL_REFERENCE),
            "thresholds": {
                "max_mean_shift_pooled_sigma": thresholds[
                    "max_mean_shift_pooled_sigma"
                ],
                "max_sd_fractional_difference": thresholds[
                    "max_sd_fractional_difference"
                ],
            },
            **comparison,
        },
        "delta_chi2": delta,
        "convergence": {
            "status": "PASS" if convergence_pass else "FAIL",
            "source": display_path(FINAL_STOP_AUDIT),
            "post_termination_gates_pass": convergence_pass,
            "rminus1_primary": final["post_termination_policy_gates"][
                "rminus1_primary"
            ],
            "bulk_ess_w_wa": final["post_termination_policy_gates"][
                "bulk_ess_w_wa"
            ],
            "tail_ess_w_wa": final["post_termination_policy_gates"][
                "tail_ess_w_wa"
            ],
        },
    }


def atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = audit()
    atomic_write_json(args.output, result)
    print(json.dumps({
        "status": result["status"],
        "posterior_moments": result["posterior_moments"]["status"],
        "delta_chi2": result["delta_chi2"]["status"],
        "output": display_path(args.output),
    }, sort_keys=True))
    return 0 if result["status"] in {"PASS", "PENDING_DELTA_CHI2"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
