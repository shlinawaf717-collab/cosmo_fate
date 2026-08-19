#!/usr/bin/env python3
"""QMC feasibility audit of the five normalized FS7 truncation constants."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.stats import norm, qmc

from pipeline.build_wp7_configs import SETTINGS
from pipeline.wp7_fs7 import admissible_latent_mask


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "runs/prd_extension/wp7/truncation_preflight.json"
SCRAMBLE_SEEDS = tuple(range(2026083101, 2026083109))
SOBOL_EXPONENT = 14
MAX_RELATIVE_QMC_SE = 0.05


def estimate(sigma_f: float, ell: float, exponent: int = SOBOL_EXPONENT) -> dict:
    fractions = []
    counts = []
    for seed in SCRAMBLE_SEEDS:
        unit = qmc.Sobol(d=7, scramble=True, seed=seed).random_base2(exponent)
        latent = norm.ppf(np.clip(unit, np.finfo(float).eps, 1.0 - np.finfo(float).eps))
        accepted = int(np.count_nonzero(admissible_latent_mask(latent, sigma_f, ell)))
        counts.append(accepted)
        fractions.append(accepted / len(latent))
    values = np.asarray(fractions)
    mean = float(np.mean(values))
    qmc_se = float(np.std(values, ddof=1) / np.sqrt(len(values)))
    return {
        "sigma_f": sigma_f,
        "ell": ell,
        "sobol_points_per_scramble": 2**exponent,
        "scramble_seeds": list(SCRAMBLE_SEEDS),
        "accepted_counts": counts,
        "normalization_estimate": mean,
        "qmc_standard_error_across_scrambles": qmc_se,
        "relative_qmc_standard_error": qmc_se / mean if mean else np.inf,
        "expected_raw_draws_per_accepted_draw": 1.0 / mean if mean else np.inf,
    }


def build() -> dict:
    records = [estimate(sigma, ell) for sigma, ell, _ in SETTINGS.values()]
    gates = {
        "every_setting_has_accepted_points": all(row["normalization_estimate"] > 0 for row in records),
        "relative_qmc_error_below_5pct": all(row["relative_qmc_standard_error"] < MAX_RELATIVE_QMC_SE for row in records),
    }
    return {
        "schema_version": "wp7-fs7-truncation-feasibility-v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if all(gates.values()) else "FAIL",
        "method": "eight independently scrambled Sobol sequences transformed to N(0,I)",
        "gates": gates,
        "settings": records,
        "scientific_role": "prior-normalization and direct-rejection feasibility only",
        "prior_fate_composition_calculated": False,
        "likelihood_evaluation_performed": False,
        "posterior_sampling_performed": False,
        "fate_endpoint_calculated": False,
        "evidence_authorized": False,
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
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
