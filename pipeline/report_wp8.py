#!/usr/bin/env python3
"""Generate the authorized WP8 future-continuation endpoints and audit."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import math
import os
import platform
from pathlib import Path

import numpy as np
import scipy
from scipy.special import ndtr

from pipeline.audit_wp4_f0_reproduction import atomic_write_json
from pipeline.build_wp7_configs import ROOT
from pipeline.wp8_future_continuation import (
    C3_DRAWS,
    C3_STANDARD_BOUNDS,
    GRID_SIZE,
    GRID_X,
    TAUS,
    admissible_winf_interval,
    bernoulli_mcse,
    boundary_derivative,
    c3_seed,
    continuation_derivative,
    continuation_values,
    direct_admissible,
    draw_c3_asymptotes,
    physical_fate,
    support_categories,
    systematic_weighted_indices,
    weighted_composition,
)


RESULT_ROOT = ROOT / "runs/prd_extension/wp8_future_continuation"
AUTHORIZATION = RESULT_ROOT / "authorization.json"
SOURCE_LEDGER = RESULT_ROOT / "source_history.csv.gz"
SOURCE_INVENTORY = RESULT_ROOT / "source_inventory.json"
ENDPOINTS = RESULT_ROOT / "wp8_endpoints.json"
AUDIT = RESULT_ROOT / "wp8_audit.json"

WP8_V1 = ROOT / "plan/wp8_future_continuation_protocol.json"
WP8_V2 = ROOT / "plan/wp8_future_continuation_amendment_v2.json"
EXECUTION = ROOT / "plan/wp8_execution_protocol.json"
WP7_ENDPOINTS = ROOT / "runs/prd_extension/wp7/production_system/wp7_endpoints.json"
WP7_AUDIT = ROOT / "runs/prd_extension/wp7/production_system/postprocessing_audit.json"
WP7_AUTHORIZATION = ROOT / "runs/prd_extension/wp7/production_system/postprocessing_authorization_v2.json"
PRIMARY_FINAL_AUDIT = ROOT / "runs/prd_extension/wp7/production_system/primary/external_monitor/final_stop_audit.json"
NODE_NAMES = tuple(f"fs7_w{i}" for i in range(1, 8))
PHYSICAL_LABELS = ("RIP", "DS", "DECAY", "CRUNCH", "OTHER")


class WP8ReportError(RuntimeError):
    """Raised when WP8 reporting would violate the frozen transaction."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _atomic_write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    with temporary.open("wb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def _load_source_chain(record: dict, chain_number: int, burn_fraction: float) -> dict:
    path = ROOT / record["path"]
    captured = int(record["captured_bytes"])
    if path.stat().st_size < captured:
        raise WP8ReportError(f"source chain shorter than audited prefix: {path}")
    with path.open("rb") as handle:
        prefix = handle.read(captured)
    if len(prefix) != captured or not prefix.endswith(b"\n"):
        raise WP8ReportError(f"source chain prefix is incomplete: {path}")
    if hashlib.sha256(prefix).hexdigest() != record["sha256"]:
        raise WP8ReportError(f"source chain prefix hash mismatch: {path}")
    header = prefix.splitlines()[0].decode("utf-8")
    if not header.startswith("#"):
        raise WP8ReportError(f"source chain header absent: {path}")
    columns = tuple(header[1:].split())
    wanted = ("weight", *NODE_NAMES)
    missing = [name for name in wanted if name not in columns]
    if missing:
        raise WP8ReportError(f"source chain columns missing {missing}: {path}")
    data = np.loadtxt(
        io.BytesIO(prefix),
        comments="#",
        usecols=tuple(columns.index(name) for name in wanted),
        ndmin=2,
    )
    if len(data) != int(record["rows"]) or not np.all(np.isfinite(data)):
        raise WP8ReportError(f"source chain rows are invalid: {path}")
    cut = int(len(data) * burn_fraction)
    retained = data[cut:]
    weights = np.rint(retained[:, 0]).astype(np.int64)
    if np.any(weights <= 0) or not np.allclose(retained[:, 0], weights):
        raise WP8ReportError(f"source dwell weights are invalid: {path}")
    nodes = retained[:, 1:]
    return {
        "chain": np.full(len(retained), int(chain_number), dtype=np.int16),
        "retained_row": np.arange(cut + 1, len(data) + 1, dtype=np.int64),
        "weights": weights,
        "nodes": nodes,
        "audit": {
            "chain": int(chain_number),
            "path": record["path"],
            "captured_bytes": captured,
            "prefix_sha256": record["sha256"],
            "raw_rows": int(len(data)),
            "burn_rows": int(cut),
            "retained_rows": int(len(retained)),
            "retained_weight": int(np.sum(weights)),
            "post_audit_complete_rows_excluded": int(record["post_audit_complete_rows_excluded"]),
        },
    }


def _source_history(authorization: dict, execution: dict) -> dict:
    records = authorization["source"]["chains"]
    burn = float(execution["source"]["burn_fraction_per_chain_complete_rows"])
    chains = [_load_source_chain(record, ordinal, burn) for ordinal, record in enumerate(records, 1)]
    return {
        "chain": np.concatenate([row["chain"] for row in chains]),
        "retained_row": np.concatenate([row["retained_row"] for row in chains]),
        "weights": np.concatenate([row["weights"] for row in chains]),
        "nodes": np.concatenate([row["nodes"] for row in chains]),
        "chain_audits": [row["audit"] for row in chains],
    }


def _ledger_bytes(source: dict, s1: np.ndarray) -> bytes:
    text = io.StringIO(newline="")
    writer = csv.writer(text, lineterminator="\n")
    writer.writerow(("chain", "retained_row", "weight", "w1", "s1", "c0_winf"))
    nodes = source["nodes"]
    for chain, row, weight, w1, slope, winf in zip(
        source["chain"],
        source["retained_row"],
        source["weights"],
        nodes[:, 3],
        s1,
        nodes[:, 6],
    ):
        writer.writerow(
            (
                int(chain),
                int(row),
                int(weight),
                format(float(w1), ".17g"),
                format(float(slope), ".17g"),
                format(float(winf), ".17g"),
            )
        )
    return gzip.compress(text.getvalue().encode("utf-8"), compresslevel=9, mtime=0)


def _composition(winf: np.ndarray, weights: np.ndarray) -> dict:
    labels = physical_fate(winf)
    fractions = weighted_composition(labels, weights)
    total = float(np.sum(weights))
    fractions["BOUNDARY"] = float(np.sum(weights[np.abs(winf + 1.0) <= 0.01]) / total)
    return {
        "fractions": fractions,
        "total_weight": total,
        "raw_rows_by_label": {name: int(np.count_nonzero(labels == name)) for name in PHYSICAL_LABELS},
    }


def _c2_endpoint(
    w1: np.ndarray,
    s1: np.ndarray,
    weights: np.ndarray,
    tau: float,
    interval: tuple[np.ndarray, np.ndarray, np.ndarray],
) -> dict:
    lower, upper, valid = interval
    admissible = valid & (lower <= -1.0) & (upper >= -1.0)
    accepted_weight = float(np.sum(weights[admissible]))
    total_weight = float(np.sum(weights))
    if accepted_weight <= 0:
        raise WP8ReportError(f"C2 tau={tau} rejected every source history")
    value_error = float(np.max(np.abs(continuation_values(w1, s1, -1.0, tau, 0.0) - w1)))
    derivative_error = float(
        np.max(np.abs(continuation_derivative(w1, s1, -1.0, tau, 0.0) - s1))
    )
    return {
        "tau": float(tau),
        "proposed_rows": int(len(w1)),
        "admissible_rows": int(np.count_nonzero(admissible)),
        "admissible_native_weight_fraction": accepted_weight / total_weight,
        "rejection_native_weight_fraction": 1.0 - accepted_weight / total_weight,
        "selection_conditioning": "path admissibility only",
        "fate_among_admissible": {
            "fractions": {
                "RIP": 0.0,
                "DS": 1.0,
                "DECAY": 0.0,
                "CRUNCH": 0.0,
                "OTHER": 0.0,
                "heat": 1.0,
                "non_heat": 0.0,
                "BOUNDARY": 1.0,
            },
            "accepted_native_weight": accepted_weight,
        },
        "boundary_value_max_abs_error": value_error,
        "boundary_derivative_max_abs_error": derivative_error,
    }


def _direct_membership_audit(
    w1: np.ndarray,
    s1: np.ndarray,
    winf: np.ndarray,
    tau: float,
    analytic: np.ndarray,
) -> dict:
    indices = np.linspace(0, len(w1) - 1, 512, dtype=np.int64)
    direct = direct_admissible(w1[indices], s1[indices], winf[indices], tau)
    match = bool(np.array_equal(direct, analytic[indices]))
    if not match:
        raise WP8ReportError(f"analytic/direct admissibility mismatch for C3 tau={tau}")
    return {
        "checked_proposals": int(len(indices)),
        "index_selection": "linspace(0,N-1,512,dtype=int64)",
        "exact_membership_match": True,
    }


def _c3_endpoint(
    source_w1: np.ndarray,
    source_s1: np.ndarray,
    tau: float,
    replicate: int,
    interval: tuple[np.ndarray, np.ndarray, np.ndarray],
) -> dict:
    seed = c3_seed(tau, replicate)
    winf = draw_c3_asymptotes(C3_DRAWS, seed)
    if not np.array_equal(winf, draw_c3_asymptotes(C3_DRAWS, seed)):
        raise WP8ReportError("C3 fixed-seed replay failed")
    lower, upper, valid = interval
    admissible = valid & (winf >= lower) & (winf <= upper)
    direct_audit = _direct_membership_audit(source_w1, source_s1, winf, tau, admissible)
    accepted = winf[admissible]
    if len(accepted) == 0:
        raise WP8ReportError(f"C3 tau={tau} replicate={replicate} accepted no proposal")
    composition = _composition(accepted, np.ones(len(accepted), dtype=np.int64))
    mcse = {
        name: bernoulli_mcse(composition["fractions"][name], len(accepted))
        for name in ("RIP", "DS", "DECAY", "heat")
    }
    value_error = float(
        np.max(np.abs(continuation_values(source_w1, source_s1, winf, tau, 0.0) - source_w1))
    )
    derivative_error = float(
        np.max(
            np.abs(continuation_derivative(source_w1, source_s1, winf, tau, 0.0) - source_s1)
        )
    )
    proposal_rip = float(np.mean(winf < -1.0))
    return {
        "tau": float(tau),
        "replicate": int(replicate),
        "seed": int(seed),
        "proposals": int(len(winf)),
        "accepted": int(len(accepted)),
        "rejected": int(len(winf) - len(accepted)),
        "rejection_fraction": float(1.0 - len(accepted) / len(winf)),
        "composition_label": "selection-conditioned, not a likelihood posterior update",
        "fate_among_admissible": composition,
        "fate_mcse": mcse,
        "all_fate_mcse_le_0p002": bool(max(mcse.values()) <= 0.002),
        "boundary_value_max_abs_error": value_error,
        "boundary_derivative_max_abs_error": derivative_error,
        "unconditioned_proposal_sampler_audit": {
            "P_RIP": proposal_rip,
            "P_heat": 1.0 - proposal_rip,
            "minimum_w_inf": float(np.min(winf)),
            "maximum_w_inf": float(np.max(winf)),
            "fixed_seed_exact_replay": True,
        },
        "analytic_direct_membership_audit": direct_audit,
    }


def _replicate_audit(first: dict, second: dict) -> dict:
    rows = {}
    passes = True
    for label in ("RIP", "DS", "DECAY", "heat"):
        p1 = float(first["fate_among_admissible"]["fractions"][label])
        p2 = float(second["fate_among_admissible"]["fractions"][label])
        se1, se2 = float(first["fate_mcse"][label]), float(second["fate_mcse"][label])
        tolerance = max(0.005, 3.0 * math.sqrt(se1**2 + se2**2))
        passed = abs(p1 - p2) <= tolerance
        passes &= passed
        rows[label] = {
            "absolute_difference": abs(p1 - p2),
            "tolerance": tolerance,
            "pass": bool(passed),
        }
    return {"probabilities": rows, "all_probabilities_pass": bool(passes)}


def validate_authorization(path: Path = AUTHORIZATION) -> dict:
    authorization = _load(path)
    if authorization.get("status") != "AUTHORIZED_AFTER_WP7_CLOSED_BEFORE_WP8_ENDPOINTS":
        raise WP8ReportError("WP8 authorization is absent or invalid")
    identities = {
        "v1_protocol_sha256": sha256_file(WP8_V1),
        "v2_protocol_sha256": sha256_file(WP8_V2),
        "execution_protocol_sha256": sha256_file(EXECUTION),
        "reporter_sha256": sha256_file(Path(__file__).resolve()),
        "geometry_module_sha256": sha256_file(ROOT / "pipeline/wp8_future_continuation.py"),
        "wp7_endpoints_sha256": sha256_file(WP7_ENDPOINTS),
        "wp7_postprocessing_audit_sha256": sha256_file(WP7_AUDIT),
        "wp7_authorization_sha256": sha256_file(WP7_AUTHORIZATION),
        "wp7_primary_final_stop_audit_sha256": sha256_file(PRIMARY_FINAL_AUDIT),
    }
    for key, current in identities.items():
        if authorization.get(key) != current:
            raise WP8ReportError(f"WP8 authorization identity mismatch: {key}")
    return authorization


def build_report(authorization: dict) -> tuple[dict, bytes, dict]:
    execution = _load(EXECUTION)
    wp7 = _load(WP7_ENDPOINTS)
    source = _source_history(authorization, execution)
    weights, nodes = source["weights"], source["nodes"]
    w1, c0_winf = nodes[:, 3], nodes[:, 6]
    s1 = boundary_derivative(nodes)
    ledger = _ledger_bytes(source, s1)

    c0 = _composition(c0_winf, weights)
    archived = wp7["settings"]["primary"]["posterior_fate"]["fractions"]
    mapping = {"RIP": "RIP", "DS": "DS", "DECAY": "DECAY", "CRUNCH": "CRUNCH", "OTHER": "OTHER"}
    reproduction_errors = {
        label: abs(c0["fractions"][label] - float(archived[source_label]))
        for label, source_label in mapping.items()
    }
    reproduction_errors["BOUNDARY"] = abs(c0["fractions"]["BOUNDARY"] - float(archived["BOUNDARY"]))
    c0_reproduction = max(reproduction_errors.values())
    if c0_reproduction > 1e-10:
        raise WP8ReportError("C0 does not reproduce the archived WP7 endpoint")

    c1 = _composition(w1, weights)
    native_intervals = {tau: admissible_winf_interval(w1, s1, tau) for tau in TAUS}
    c2 = {
        str(tau): _c2_endpoint(w1, s1, weights, tau, native_intervals[tau]) for tau in TAUS
    }
    c2_admissible = [
        valid & (lower <= -1.0) & (upper >= -1.0)
        for lower, upper, valid in native_intervals.values()
    ]
    categories = support_categories(c0_winf, c2_admissible, native_intervals.values())
    category_total = float(np.sum(weights))
    category_fractions = {
        label: float(np.sum(weights[categories == label]) / category_total)
        for label in ("{RIP}", "{heat}", "{RIP,heat}", "empty/invalid")
    }
    if category_fractions["empty/invalid"] != 0:
        raise WP8ReportError("partial-identification support is empty for a source row")

    source_indices = systematic_weighted_indices(weights, C3_DRAWS)
    sampled_w1, sampled_s1 = w1[source_indices], s1[source_indices]
    c3 = {}
    replicate_pass = True
    all_mcse_pass = True
    boundary_pass = True
    for tau in TAUS:
        interval = admissible_winf_interval(sampled_w1, sampled_s1, tau)
        first = _c3_endpoint(sampled_w1, sampled_s1, tau, 1, interval)
        second = _c3_endpoint(sampled_w1, sampled_s1, tau, 2, interval)
        replicate = _replicate_audit(first, second)
        replicate_pass &= replicate["all_probabilities_pass"]
        all_mcse_pass &= first["all_fate_mcse_le_0p002"] and second["all_fate_mcse_le_0p002"]
        boundary_pass &= max(
            first["boundary_value_max_abs_error"],
            first["boundary_derivative_max_abs_error"],
            second["boundary_value_max_abs_error"],
            second["boundary_derivative_max_abs_error"],
        ) <= 1e-10
        c3[str(tau)] = {"replicate_1": first, "replicate_2": second, "replicate_audit": replicate}

    registered_rows = {
        "C0": c0["fractions"],
        "C1": c1["fractions"],
    }
    for tau, row in c2.items():
        registered_rows[f"C2_tau_{tau}"] = row["fate_among_admissible"]["fractions"]
    for tau, row in c3.items():
        registered_rows[f"C3_tau_{tau}"] = row["replicate_1"]["fate_among_admissible"]["fractions"]
    rip_values = [row["RIP"] for row in registered_rows.values()]
    heat_values = [row["heat"] for row in registered_rows.values()]

    source_inventory = {
        "schema_version": "wp8-source-history-inventory-v1",
        "source_setting": "WP7 primary audited prefixes",
        "chains": source["chain_audits"],
        "pooled_retained_rows": int(len(weights)),
        "pooled_retained_weight": int(np.sum(weights)),
        "ledger": {
            "path": str(SOURCE_LEDGER.relative_to(ROOT)),
            "sha256": hashlib.sha256(ledger).hexdigest(),
            "gzip_mtime": 0,
            "rows_excluding_header": int(len(weights)),
        },
    }
    gates = {
        "C0_reproduces_WP7_within_1e_10": c0_reproduction <= 1e-10,
        "boundary_value_and_derivative_within_1e_10": bool(boundary_pass),
        "past_observable_and_likelihood_invariance_by_identity": True,
        "C3_fixed_seed_replay": True,
        "all_C3_fate_mcse_le_0p002": bool(all_mcse_pass),
        "all_C3_replicate_comparisons_pass": bool(replicate_pass),
        "all_analytic_direct_membership_checks_pass": True,
        "no_empty_partial_support": category_fractions["empty/invalid"] == 0,
        "no_family_model_average_calculated": True,
    }
    payload = {
        "schema_version": "wp8-future-continuation-endpoints-v1",
        "status": "PASS" if all(gates.values()) else "FAIL",
        "authorization_sha256": sha256_file(AUTHORIZATION),
        "source_inventory_sha256": hashlib.sha256(
            (json.dumps(source_inventory, indent=2, sort_keys=True) + "\n").encode()
        ).hexdigest(),
        "source_history": {
            "rows": int(len(weights)),
            "native_weight": int(np.sum(weights)),
            "systematic_C3_history_draws": C3_DRAWS,
            "boundary_state": {
                "w1_weighted_mean": float(np.sum(weights * w1) / np.sum(weights)),
                "s1_weighted_mean": float(np.sum(weights * s1) / np.sum(weights)),
            },
        },
        "families": {
            "C0_frozen_FS7": {
                **c0,
                "WP7_reproduction_max_abs_error": c0_reproduction,
                "WP7_reproduction_errors": reproduction_errors,
            },
            "C1_present_constant_diagnostic": c1,
            "C2_relax_to_lambda": c2,
            "C3_matched_free_asymptote": {
                "unconditioned_measure": {
                    "P_RIP": 0.5,
                    "P_heat": 0.5,
                    "P_DS": 0.0,
                    "likelihood_information": 0.0,
                    "normalization_mass_before_renormalization": float(
                        ndtr(C3_STANDARD_BOUNDS[1]) - ndtr(C3_STANDARD_BOUNDS[0])
                    ),
                },
                "settings": c3,
            },
        },
        "partial_identification": {
            "categories": category_fractions,
            "denominator_native_weight": category_total,
            "threshold": None,
            "interpretation": "support set across C0, admissible C2, and complete admissible C3 intervals",
        },
        "descriptive_continuation_envelope": {
            "registered_rows": registered_rows,
            "P_RIP": {"minimum": min(rip_values), "maximum": max(rip_values), "span": max(rip_values) - min(rip_values)},
            "P_heat": {"minimum": min(heat_values), "maximum": max(heat_values), "span": max(heat_values) - min(heat_values)},
            "family_probabilities_assigned": False,
        },
        "validation": {
            "gates": gates,
            "past_invariance": {
                "maximum_history_difference_for_a_le_1": 0.0,
                "maximum_observable_difference_for_z_ge_0": 0.0,
                "maximum_loglike_difference": 0.0,
                "basis": "alternative continuation calls the identical registered FS7 history branch for a<=1",
            },
        },
    }
    return payload, ledger, source_inventory


def report(
    authorization_path: Path = AUTHORIZATION,
    endpoint_path: Path = ENDPOINTS,
    audit_path: Path = AUDIT,
    ledger_path: Path = SOURCE_LEDGER,
    inventory_path: Path = SOURCE_INVENTORY,
) -> dict:
    outputs = (endpoint_path, audit_path, ledger_path, inventory_path)
    if any(path.exists() for path in outputs):
        raise WP8ReportError("refusing to overwrite an existing WP8 release artifact")
    authorization = validate_authorization(authorization_path)
    payload, ledger, source_inventory = build_report(authorization)
    if payload["status"] != "PASS":
        raise WP8ReportError("WP8 validation gate failed; no release artifact written")
    _atomic_write_bytes(ledger_path, ledger)
    atomic_write_json(inventory_path, source_inventory)
    if payload["source_inventory_sha256"] != sha256_file(inventory_path):
        raise WP8ReportError("source inventory serialization hash mismatch")
    atomic_write_json(endpoint_path, payload)
    audit = {
        "schema_version": "wp8-future-continuation-audit-v1",
        "status": payload["status"],
        "authorization_sha256": sha256_file(authorization_path),
        "artifacts": {
            "source_ledger": {"path": str(ledger_path.relative_to(ROOT)), "sha256": sha256_file(ledger_path)},
            "source_inventory": {"path": str(inventory_path.relative_to(ROOT)), "sha256": sha256_file(inventory_path)},
            "endpoints": {"path": str(endpoint_path.relative_to(ROOT)), "sha256": sha256_file(endpoint_path)},
        },
        "reporter_sha256": sha256_file(Path(__file__).resolve()),
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "platform": platform.platform(),
        },
        "gates": payload["validation"]["gates"],
        "family_model_average_calculated": False,
        "secondary_full_cmb_calculated": False,
    }
    atomic_write_json(audit_path, audit)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authorization", type=Path, default=AUTHORIZATION)
    parser.add_argument("--output", type=Path, default=ENDPOINTS)
    parser.add_argument("--audit", type=Path, default=AUDIT)
    parser.add_argument("--ledger", type=Path, default=SOURCE_LEDGER)
    parser.add_argument("--inventory", type=Path, default=SOURCE_INVENTORY)
    args = parser.parse_args()
    payload = report(
        args.authorization.resolve(),
        args.output.resolve(),
        args.audit.resolve(),
        args.ledger.resolve(),
        args.inventory.resolve(),
    )
    print(json.dumps({"status": payload["status"], "output": str(args.output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
