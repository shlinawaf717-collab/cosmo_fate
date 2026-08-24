#!/usr/bin/env python3
"""Independently re-audit the frozen WP8 release from its source ledger."""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
from pathlib import Path

import numpy as np

from pipeline.audit_wp4_f0_reproduction import atomic_write_json
from pipeline.build_wp7_configs import ROOT
from pipeline.report_wp8 import (
    AUDIT,
    AUTHORIZATION,
    ENDPOINTS,
    SOURCE_INVENTORY,
    SOURCE_LEDGER,
    sha256_file,
)
from pipeline.wp8_future_continuation import (
    C3_DRAWS,
    TAUS,
    admissible_winf_interval,
    c3_seed,
    draw_c3_asymptotes,
    systematic_weighted_indices,
)


OUTPUT = ROOT / "runs/prd_extension/wp8_future_continuation/completion_audit.json"


class WP8CompletionError(RuntimeError):
    """Raised when a frozen WP8 release invariant fails."""


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_ledger(path: Path) -> dict[str, np.ndarray]:
    with gzip.open(path, "rt", encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise WP8CompletionError("WP8 source ledger is empty")
    expected = {"chain", "retained_row", "weight", "w1", "s1", "c0_winf"}
    if set(rows[0]) != expected:
        raise WP8CompletionError("WP8 source ledger columns differ from the freeze")
    result = {
        "chain": np.asarray([int(row["chain"]) for row in rows], dtype=np.int16),
        "retained_row": np.asarray([int(row["retained_row"]) for row in rows], dtype=np.int64),
        "weight": np.asarray([int(row["weight"]) for row in rows], dtype=np.int64),
        "w1": np.asarray([float(row["w1"]) for row in rows], dtype=np.float64),
        "s1": np.asarray([float(row["s1"]) for row in rows], dtype=np.float64),
        "c0_winf": np.asarray([float(row["c0_winf"]) for row in rows], dtype=np.float64),
    }
    if np.any(result["weight"] <= 0) or not all(np.all(np.isfinite(row)) for row in result.values()):
        raise WP8CompletionError("WP8 source ledger contains an invalid value")
    pairs = np.column_stack((result["chain"], result["retained_row"]))
    if len(np.unique(pairs, axis=0)) != len(pairs):
        raise WP8CompletionError("WP8 source ledger contains duplicate chain rows")
    return result


def _weighted_fraction(mask: np.ndarray, weights: np.ndarray) -> float:
    return float(np.sum(weights[np.asarray(mask, dtype=bool)]) / np.sum(weights))


def build_audit() -> dict:
    for path in (AUTHORIZATION, SOURCE_LEDGER, SOURCE_INVENTORY, ENDPOINTS, AUDIT):
        if not path.is_file():
            raise WP8CompletionError(f"required WP8 artifact is missing: {path}")
    endpoint, release_audit, inventory = _load(ENDPOINTS), _load(AUDIT), _load(SOURCE_INVENTORY)
    if endpoint.get("status") != "PASS" or release_audit.get("status") != "PASS":
        raise WP8CompletionError("WP8 endpoint or release audit is not PASS")
    artifact_hashes = {
        "source_ledger": sha256_file(SOURCE_LEDGER),
        "source_inventory": sha256_file(SOURCE_INVENTORY),
        "endpoints": sha256_file(ENDPOINTS),
    }
    for name, current in artifact_hashes.items():
        if release_audit["artifacts"][name]["sha256"] != current:
            raise WP8CompletionError(f"WP8 release hash mismatch: {name}")
    if inventory["ledger"]["sha256"] != artifact_hashes["source_ledger"]:
        raise WP8CompletionError("WP8 inventory/ledger hash mismatch")

    ledger = _load_ledger(SOURCE_LEDGER)
    weights, w1, s1, c0 = (
        ledger["weight"],
        ledger["w1"],
        ledger["s1"],
        ledger["c0_winf"],
    )
    if len(weights) != inventory["pooled_retained_rows"] or int(np.sum(weights)) != inventory[
        "pooled_retained_weight"
    ]:
        raise WP8CompletionError("WP8 source row/weight accounting mismatch")
    c0_rip = _weighted_fraction(c0 < -1.0, weights)
    c1_rip = _weighted_fraction(w1 < -1.0, weights)
    expected_c0 = endpoint["families"]["C0_frozen_FS7"]["fractions"]["RIP"]
    expected_c1 = endpoint["families"]["C1_present_constant_diagnostic"]["fractions"]["RIP"]
    if not math.isclose(c0_rip, expected_c0, abs_tol=1e-15) or not math.isclose(
        c1_rip, expected_c1, abs_tol=1e-15
    ):
        raise WP8CompletionError("WP8 C0/C1 ledger recomputation mismatch")

    support = {}
    all_cross = np.ones(len(weights), dtype=bool)
    for tau in TAUS:
        lower, upper, valid = admissible_winf_interval(w1, s1, tau)
        crosses = valid & (lower < -1.0) & (upper >= -1.0)
        full = valid & (lower == -3.0) & (upper == 1.0)
        all_cross &= crosses
        support[str(tau)] = {
            "valid_native_weight_fraction": _weighted_fraction(valid, weights),
            "crosses_fate_boundary_native_weight_fraction": _weighted_fraction(crosses, weights),
            "full_minus3_to_plus1_native_weight_fraction": _weighted_fraction(full, weights),
            "minimum_lower_endpoint": float(np.min(lower[valid])),
            "maximum_lower_endpoint": float(np.max(lower[valid])),
            "minimum_upper_endpoint": float(np.min(upper[valid])),
            "maximum_upper_endpoint": float(np.max(upper[valid])),
        }

    source_indices = systematic_weighted_indices(weights, C3_DRAWS)
    paired_w1, paired_s1 = w1[source_indices], s1[source_indices]
    c3_recomputation = {}
    for tau in TAUS:
        lower, upper, valid = admissible_winf_interval(paired_w1, paired_s1, tau)
        c3_recomputation[str(tau)] = {}
        for replicate in (1, 2):
            winf = draw_c3_asymptotes(C3_DRAWS, c3_seed(tau, replicate))
            accepted = valid & (winf >= lower) & (winf <= upper)
            count = int(np.count_nonzero(accepted))
            rip = int(np.count_nonzero(accepted & (winf < -1.0)))
            probability = rip / count
            recorded = endpoint["families"]["C3_matched_free_asymptote"]["settings"][str(tau)][
                f"replicate_{replicate}"
            ]
            if count != recorded["accepted"] or not math.isclose(
                probability,
                recorded["fate_among_admissible"]["fractions"]["RIP"],
                abs_tol=1e-15,
            ):
                raise WP8CompletionError(f"WP8 C3 recomputation mismatch: {tau}/{replicate}")
            c3_recomputation[str(tau)][f"replicate_{replicate}"] = {
                "accepted": count,
                "RIP": probability,
                "exact_match": True,
            }

    partial = endpoint["partial_identification"]["categories"]
    cross_fraction = _weighted_fraction(all_cross, weights)
    gates = {
        "release_artifact_hashes_match": True,
        "source_rows_unique": True,
        "source_row_and_weight_totals_match": True,
        "C0_C1_recomputed_exactly": True,
        "all_tau_supports_cross_fate_boundary_for_all_native_weight": cross_fraction == 1.0,
        "partial_identification_is_two_sided_for_all_native_weight": partial["{RIP,heat}"] == 1.0,
        "all_six_C3_ledgers_recomputed_exactly": True,
        "release_validation_gates_all_pass": all(release_audit["gates"].values()),
        "no_family_model_average": not release_audit["family_model_average_calculated"],
    }
    return {
        "schema_version": "wp8-future-continuation-completion-audit-v1",
        "status": "PASS" if all(gates.values()) else "FAIL",
        "release_artifact_hashes": artifact_hashes,
        "source": {
            "rows": int(len(weights)),
            "native_weight": int(np.sum(weights)),
            "C0_P_RIP_recomputed": c0_rip,
            "C1_P_RIP_recomputed": c1_rip,
        },
        "analytic_C3_support": support,
        "all_tau_cross_boundary_native_weight_fraction": cross_fraction,
        "C3_recomputation": c3_recomputation,
        "gates": gates,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    if args.output.exists():
        raise WP8CompletionError("refusing to overwrite an existing WP8 completion audit")
    payload = build_audit()
    atomic_write_json(args.output.resolve(), payload)
    print(json.dumps({"status": payload["status"], "output": str(args.output)}, sort_keys=True))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
