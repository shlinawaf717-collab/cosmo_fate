#!/usr/bin/env python3
"""Generate the authorized WP7 FS7 real-data endpoints and audit."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import platform
import sys
from pathlib import Path
from typing import Sequence

import numpy as np
import scipy

from pipeline.audit_wp4_f0_reproduction import atomic_write_json
from pipeline.build_wp7_configs import ROOT, SETTINGS
from pipeline.fate import Background, OMEGA_R_H2, classify
from pipeline.wp7_fs7 import (
    FREE_A_NODES,
    cholesky,
    conditional_future_geometry,
    draw_truncated_latents,
    make_ln_fde,
    w_of_a,
)


SYSTEM = ROOT / "runs/prd_extension/wp7/production_system"
AUTHORIZATION_V1 = SYSTEM / "postprocessing_authorization.json"
AUTHORIZATION = SYSTEM / "postprocessing_authorization_v2.json"
ENDPOINTS = SYSTEM / "wp7_endpoints.json"
AUDIT = SYSTEM / "postprocessing_audit.json"
PROTOCOL = ROOT / "plan/wp7_postprocessing_protocol.json"
INFORMATION_PLAN = ROOT / "runs/prd_extension/wp7/information_plan.json"
SBC_REPORT = ROOT / "runs/prd_extension/wp7/sbc/sbc_report.json"
NODE_NAMES = tuple(f"fs7_w{i}" for i in range(1, 8))
QUANTILES = (0.025, 0.16, 0.5, 0.84, 0.975)
FATE_LABELS = ("RIP", "DS", "DECAY", "CRUNCH", "OTHER")


class WP7ReportError(RuntimeError):
    """Raised when final reporting would violate the frozen authorization."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _header_from_prefix(prefix: bytes, path: Path) -> tuple[str, ...]:
    line = prefix.splitlines()[0].decode("utf-8")
    if not line.startswith("#"):
        raise WP7ReportError(f"missing Cobaya header: {path}")
    return tuple(line[1:].split())


def _load_postburn_chain(path: Path, expected: dict, burn_fraction: float) -> dict:
    if path.stat().st_size < expected["captured_bytes"]:
        raise WP7ReportError(f"chain is shorter than its audited prefix: {path}")
    with path.open("rb") as handle:
        prefix = handle.read(expected["captured_bytes"])
    if len(prefix) != expected["captured_bytes"] or not prefix.endswith(b"\n"):
        raise WP7ReportError(f"audited chain prefix is incomplete: {path}")
    if hashlib.sha256(prefix).hexdigest() != expected["sha256"]:
        raise WP7ReportError(f"audited chain prefix hash mismatch: {path}")
    columns = _header_from_prefix(prefix, path)
    wanted = ("weight", "omegam", "H0", *NODE_NAMES)
    missing = [name for name in wanted if name not in columns]
    if missing:
        raise WP7ReportError(f"chain columns missing {missing}: {path}")
    usecols = tuple(columns.index(name) for name in wanted)
    data = np.loadtxt(io.BytesIO(prefix), comments="#", usecols=usecols, ndmin=2)
    if data.shape[0] != expected["rows"]:
        raise WP7ReportError(f"chain row count mismatch: {path}")
    if not np.all(np.isfinite(data)):
        raise WP7ReportError(f"non-finite chain value: {path}")
    cut = int(data.shape[0] * burn_fraction)
    retained = data[cut:]
    weights = np.rint(retained[:, 0]).astype(np.int64)
    if np.any(weights <= 0) or not np.allclose(retained[:, 0], weights):
        raise WP7ReportError(f"invalid integer dwell weights: {path}")
    return {
        "path": str(path.relative_to(ROOT)),
        "raw_rows": int(data.shape[0]),
        "burn_rows": int(cut),
        "retained_rows": int(len(retained)),
        "retained_weight": int(weights.sum()),
        "post_audit_complete_rows_excluded": int(expected["post_audit_complete_rows_excluded"]),
        "post_audit_bytes_excluded": int(expected["post_audit_bytes_excluded"]),
        "weights": weights,
        "omegam": retained[:, 1],
        "H0": retained[:, 2],
        "nodes": retained[:, 3:],
    }


def weighted_summary(values: np.ndarray, weights: np.ndarray) -> dict:
    values = np.asarray(values, dtype=np.float64)
    weights = np.asarray(weights, dtype=np.float64)
    if values.ndim != 1 or weights.shape != values.shape or len(values) == 0:
        raise WP7ReportError("weighted summary arrays are incompatible")
    if np.any(~np.isfinite(values)) or np.any(~np.isfinite(weights)) or np.any(weights <= 0):
        raise WP7ReportError("weighted summary inputs are invalid")
    order = np.argsort(values, kind="mergesort")
    sorted_values, sorted_weights = values[order], weights[order]
    cumulative = np.cumsum(sorted_weights)
    total = float(cumulative[-1])
    quantile_values = []
    for probability in QUANTILES:
        index = int(np.searchsorted(cumulative, probability * total, side="left"))
        quantile_values.append(float(sorted_values[min(index, len(sorted_values) - 1)]))
    mean = float(np.sum(weights * values) / total)
    variance = float(np.sum(weights * (values - mean) ** 2) / total)
    return {
        "mean": mean,
        "population_sd": float(math.sqrt(max(variance, 0.0))),
        "quantiles": {str(q): value for q, value in zip(QUANTILES, quantile_values)},
        "total_weight": total,
    }


def quantile_bin_kl(
    values: np.ndarray, weights: np.ndarray, frozen_edges: Sequence[float]
) -> dict:
    values = np.asarray(values, dtype=np.float64)
    weights = np.asarray(weights, dtype=np.float64)
    edges = np.asarray(frozen_edges, dtype=np.float64).copy()
    bins = len(edges) - 1
    if bins < 2 or np.any(np.diff(edges) <= 0):
        raise WP7ReportError("invalid frozen prior quantile edges")
    edges[0], edges[-1] = -np.inf, np.inf
    mass, _ = np.histogram(values, bins=edges, weights=weights)
    total = float(np.sum(mass))
    if not np.isclose(total, float(np.sum(weights)), rtol=1e-12, atol=1e-8):
        raise WP7ReportError("KL histogram did not conserve posterior weight")
    probabilities = mass / total
    positive = probabilities > 0
    kl = float(np.sum(probabilities[positive] * np.log(probabilities[positive] * bins)))
    return {
        "bins": bins,
        "kl_nats": kl,
        "occupied_bins": int(np.count_nonzero(positive)),
        "posterior_mass_conserved": True,
    }


def _sign_batch_mcse(chains: Sequence[dict], batches_per_chain: int = 32) -> dict:
    expanded = [np.repeat(chain["nodes"][:, -1], chain["weights"]) for chain in chains]
    common = min(len(array) for array in expanded)
    usable = common - common % batches_per_chain
    if usable < batches_per_chain * 10:
        raise WP7ReportError("too few post-burn weighted draws for sign MCSE")
    means = []
    for array in expanded:
        indicator = (array[-usable:] < -1.0).astype(np.float64)
        means.extend(block.mean() for block in np.split(indicator, batches_per_chain))
    result = float(np.std(means, ddof=1) / np.sqrt(len(means)))
    return {
        "mcse": result,
        "batches_per_chain": int(batches_per_chain),
        "total_batches": int(len(means)),
        "equalized_expanded_draws_per_chain": int(usable),
        "passes_registered_0p01_gate": result < 0.01,
    }


def _classify_posterior(
    nodes: np.ndarray, omegam: np.ndarray, H0: np.ndarray, weights: np.ndarray
) -> dict:
    h2 = (H0 / 100.0) ** 2
    ode = 1.0 - omegam - OMEGA_R_H2 / h2
    labels = np.full(len(nodes), "OTHER", dtype="U8")
    positive = ode > 0
    winf = nodes[:, -1]
    labels[positive & (winf < -1.0)] = "RIP"
    labels[positive & (winf == -1.0)] = "DS"
    labels[positive & (winf > -1.0)] = "DECAY"
    fallback_indices = np.flatnonzero(~positive)
    for index in fallback_indices:
        history = nodes[index]
        background = Background(
            omegam=float(omegam[index]),
            H0=float(H0[index]),
            ln_fde=make_ln_fde(history),
            w_of_a=lambda a, fixed=history: w_of_a(a, fixed),
            w_inf=float(history[-1]),
        )
        labels[index] = classify(background)[0]
    total = float(np.sum(weights))
    fractions = {
        label: float(np.sum(weights[labels == label]) / total) for label in FATE_LABELS
    }
    boundary = np.abs(winf + 1.0) <= 0.01
    fractions["BOUNDARY"] = float(np.sum(weights[boundary]) / total)
    fractions["heat_death_compatible"] = fractions["DS"] + fractions["DECAY"]
    fractions["non_heat_death"] = fractions["RIP"] + fractions["CRUNCH"]
    fractions["unclassified"] = fractions["OTHER"]
    return {
        "fractions": fractions,
        "raw_rows_by_label": {label: int(np.count_nonzero(labels == label)) for label in FATE_LABELS},
        "nonpositive_dark_energy_rows_sent_to_frozen_classifier": int(len(fallback_indices)),
        "total_weight": total,
        "physical_boundary_rule": "exact w_inf=-1; abs(w_inf+1)<=0.01 is a separate boundary flag",
    }


def _classify_prior(nodes: np.ndarray) -> dict:
    winf = nodes[:, -1]
    count = len(winf)
    rip = int(np.count_nonzero(winf < -1.0))
    ds = int(np.count_nonzero(winf == -1.0))
    decay = int(np.count_nonzero(winf > -1.0))
    boundary = int(np.count_nonzero(np.abs(winf + 1.0) <= 0.01))
    fractions = {
        "RIP": rip / count,
        "DS": ds / count,
        "DECAY": decay / count,
        "CRUNCH": 0.0,
        "OTHER": 0.0,
        "BOUNDARY": boundary / count,
        "heat_death_compatible": (ds + decay) / count,
        "non_heat_death": rip / count,
        "unclassified": 0.0,
    }
    p = fractions["RIP"]
    return {
        "fractions": fractions,
        "draws": count,
        "rip_bernoulli_mcse": float(math.sqrt(p * (1.0 - p) / count)),
        "conditioning": "registered normalized FS7 function prior with positive present-day dark-energy density",
    }


def _residual(nodes: np.ndarray, geometry: dict) -> np.ndarray:
    observed = np.asarray(geometry["observed_indices"], dtype=np.int64)
    coefficients = np.asarray(geometry["conditional_mean_weights"], dtype=np.float64)
    return (nodes[:, -1] + 1.0) - (nodes[:, observed] + 1.0) @ coefficients


def _regenerate_prior(tag: str, record: dict) -> tuple[np.ndarray, dict]:
    latent, rejection = draw_truncated_latents(
        int(record["draws"]),
        float(record["sigma_f"]),
        float(record["ell"]),
        seed=int(record["seed"]),
        batch_size=int(record["rejection_audit"]["batch_size"]),
    )
    nodes = -1.0 + latent @ cholesky(record["sigma_f"], record["ell"]).T
    geometry = record["conditional_future_geometry"]
    variables = {f"fs7_w{i}": nodes[:, i - 1] for i in range(1, 8)}
    variables["a4_conditional_residual"] = _residual(nodes, geometry)
    max_edge_difference = 0.0
    for name, values in variables.items():
        for bins, frozen in record["quantile_edges"][name].items():
            regenerated = np.quantile(values, np.linspace(0.0, 1.0, int(bins) + 1))
            max_edge_difference = max(
                max_edge_difference,
                float(np.max(np.abs(regenerated - np.asarray(frozen, dtype=np.float64)))),
            )
    if max_edge_difference > 1.0e-12:
        raise WP7ReportError(f"prior reference did not reproduce for {tag}")
    return nodes, {
        "rejection_audit": rejection,
        "maximum_abs_reproduced_quantile_edge_difference": max_edge_difference,
        "quantile_edges_reproduced": True,
    }


def validate_authorization(path: Path = AUTHORIZATION) -> dict:
    authorization = _load(path)
    if authorization.get("status") != "AUTHORIZED_AFTER_ALL_SETTINGS_CLOSED_BEFORE_ENDPOINTS":
        raise WP7ReportError("WP7 post-processing authorization is absent or invalid")
    identities = {
        "postprocessing_protocol_sha256": sha256_file(PROTOCOL),
        "information_plan_sha256": sha256_file(INFORMATION_PLAN),
        "sbc_report_sha256": sha256_file(SBC_REPORT),
        "reporter_sha256": sha256_file(Path(__file__).resolve()),
    }
    for key, current in identities.items():
        if authorization.get(key) != current:
            raise WP7ReportError(f"authorization identity mismatch: {key}")
    if not authorization.get("fate_calculation_authorized"):
        raise WP7ReportError("fate calculation was not authorized")
    return authorization


def _setting_report(tag: str, authorization: dict, information: dict, protocol: dict) -> dict:
    burn = float(protocol["pooling"]["burn_fraction_per_chain_by_complete_rows"])
    chain_records = authorization["settings"][tag]["chains"]
    chains = [
        _load_postburn_chain(ROOT / record["path"], record, burn) for record in chain_records
    ]
    weights = np.concatenate([chain["weights"] for chain in chains])
    nodes = np.concatenate([chain["nodes"] for chain in chains])
    omegam = np.concatenate([chain["omegam"] for chain in chains])
    H0 = np.concatenate([chain["H0"] for chain in chains])
    prior_record = information["prior_reference"][tag]
    prior_nodes, reproduction = _regenerate_prior(tag, prior_record)
    geometry = prior_record["conditional_future_geometry"]
    posterior_residual = _residual(nodes, geometry)
    prior_residual = _residual(prior_nodes, geometry)
    node_reports = {}
    for index, name in enumerate(NODE_NAMES):
        node_reports[name] = {
            "a": float(FREE_A_NODES[index]),
            "region": "observed_history" if FREE_A_NODES[index] <= 1.0 else "future_continuation",
            "posterior": weighted_summary(nodes[:, index], weights),
            "kl": {
                bins: quantile_bin_kl(
                    nodes[:, index], weights, prior_record["quantile_edges"][name][bins]
                )
                for bins in ("20", "40", "80")
            },
        }
    residual_report = {
        "posterior": weighted_summary(posterior_residual, weights),
        "prior": weighted_summary(prior_residual, np.ones(len(prior_residual))),
        "kl": {
            bins: quantile_bin_kl(
                posterior_residual,
                weights,
                prior_record["quantile_edges"]["a4_conditional_residual"][bins],
            )
            for bins in ("20", "40", "80")
        },
        "registered_negligible_kl_threshold": None,
        "binary_negligible_information_verdict_authorized": False,
    }
    posterior_fate = _classify_posterior(nodes, omegam, H0, weights)
    posterior_fate["rip_batch_mcse"] = _sign_batch_mcse(chains)
    return {
        "hyperparameters": {
            "sigma_f": float(prior_record["sigma_f"]),
            "ell": float(prior_record["ell"]),
        },
        "chains": [
            {key: chain[key] for key in (
                "path", "raw_rows", "burn_rows", "retained_rows", "retained_weight",
                "post_audit_complete_rows_excluded", "post_audit_bytes_excluded",
            )}
            for chain in chains
        ],
        "pooled_retained_rows": int(sum(chain["retained_rows"] for chain in chains)),
        "pooled_retained_weight": int(np.sum(weights)),
        "prior_reference": {
            **reproduction,
            "fate": _classify_prior(prior_nodes),
        },
        "posterior_fate": posterior_fate,
        "node_information": node_reports,
        "conditional_future_geometry": geometry,
        "conditional_final_node_residual": residual_report,
    }


def build_report(authorization: dict, protocol: dict, information: dict, sbc: dict) -> dict:
    settings = {
        tag: _setting_report(tag, authorization, information, protocol) for tag in SETTINGS
    }
    primary_rip = settings["primary"]["posterior_fate"]["fractions"]["RIP"]
    sensitivity = {
        tag: {
            "posterior_rip_probability": record["posterior_fate"]["fractions"]["RIP"],
            "delta_from_primary": record["posterior_fate"]["fractions"]["RIP"] - primary_rip,
            "boundary_fraction": record["posterior_fate"]["fractions"]["BOUNDARY"],
            "other_fraction": record["posterior_fate"]["fractions"]["OTHER"],
            "final_node_kl_40_nats": record["node_information"]["fs7_w7"]["kl"]["40"]["kl_nats"],
            "conditional_residual_kl_40_nats": record["conditional_final_node_residual"]["kl"]["40"]["kl_nats"],
        }
        for tag, record in settings.items()
    }
    rip_values = [row["posterior_rip_probability"] for row in sensitivity.values()]
    all_mcse_pass = all(
        row["posterior_fate"]["rip_batch_mcse"]["passes_registered_0p01_gate"]
        for row in settings.values()
    )
    return {
        "schema_version": "wp7-fs7-endpoints-v1",
        "status": "PASS" if all_mcse_pass and sbc["status"] == "PASS" else "FAIL",
        "authorization_sha256": sha256_file(AUTHORIZATION),
        "postprocessing_protocol_sha256": sha256_file(PROTOCOL),
        "information_plan_sha256": sha256_file(INFORMATION_PLAN),
        "sbc": {
            "status": sbc["status"],
            "datasets": sbc["datasets"],
            "gates": sbc["gates"],
            "report_sha256": sha256_file(SBC_REPORT),
        },
        "settings": settings,
        "sensitivity_summary": {
            "by_setting": sensitivity,
            "posterior_rip_probability_range": [float(min(rip_values)), float(max(rip_values))],
            "maximum_absolute_delta_from_primary": float(
                max(abs(row["delta_from_primary"]) for row in sensitivity.values())
            ),
        },
        "information_pathways": {
            "prior_correlation": "setting-specific conditional geometry in each setting record",
            "global_spline_likelihood_response": information["likelihood_window_response"],
            "conditional_residual_KL": "setting-specific 20/40/80-bin endpoint",
        },
        "analytic_prediction": {
            "registered_statement": "P(RIP) approaches one half when the final-node prior is symmetric and the likelihood adds negligible conditional-residual information",
            "prior_symmetry_structural": True,
            "condition_2_reported_quantitatively_without_post_result_threshold": True,
            "binary_prediction_verdict_authorized": False,
        },
        "gates": {
            "all_five_settings_reported": len(settings) == 5,
            "all_posterior_rip_mcse_lt_0p01": all_mcse_pass,
            "sbc_pass": sbc["status"] == "PASS" and all(sbc["gates"].values()),
            "no_model_evidence_calculated": True,
            "all_endpoints_use_final_stop_audited_prefixes_only": True,
        },
    }


def report(
    authorization_path: Path = AUTHORIZATION,
    endpoint_path: Path = ENDPOINTS,
    audit_path: Path = AUDIT,
) -> dict:
    if endpoint_path.exists() or audit_path.exists():
        raise WP7ReportError("refusing to overwrite an existing WP7 final artifact")
    authorization = validate_authorization(authorization_path)
    protocol, information, sbc = _load(PROTOCOL), _load(INFORMATION_PLAN), _load(SBC_REPORT)
    payload = build_report(authorization, protocol, information, sbc)
    atomic_write_json(endpoint_path, payload)
    audit = {
        "schema_version": "wp7-fs7-postprocessing-audit-v1",
        "status": payload["status"],
        "authorization_sha256": sha256_file(authorization_path),
        "endpoint": {
            "path": str(endpoint_path.relative_to(ROOT)),
            "sha256": sha256_file(endpoint_path),
        },
        "reporter_sha256": sha256_file(Path(__file__).resolve()),
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "platform": platform.platform(),
        },
        "gates": payload["gates"],
        "model_evidence_calculated": False,
        "source_inputs_unchanged": True,
    }
    atomic_write_json(audit_path, audit)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authorization", type=Path, default=AUTHORIZATION)
    parser.add_argument("--output", type=Path, default=ENDPOINTS)
    parser.add_argument("--audit", type=Path, default=AUDIT)
    args = parser.parse_args()
    payload = report(args.authorization.resolve(), args.output.resolve(), args.audit.resolve())
    print(json.dumps({"status": payload["status"], "output": str(args.output)}, sort_keys=True))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
