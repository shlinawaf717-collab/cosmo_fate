#!/usr/bin/env python3
"""Generate the six registered WP2 null500 scientific endpoints.

The completion audit establishes that the campaign is technically complete.
This separate report converts the immutable 500-noisy-mock ledger into the
versioned scientific endpoint artifact required by protocol section 5.2.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import scipy
from scipy.stats import binomtest, kstest


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUN_ROOT = ROOT / "runs" / "prd_extension" / "null500"
DEFAULT_OBSERVED = ROOT / "runs" / "phase2" / "fate" / "d0_cpl_p1.json"
SCHEMA_VERSION = "wp2-null500-endpoints-v1"


class EndpointReportError(RuntimeError):
    """Raised when a frozen input cannot support the registered report."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _exact_interval(successes: int, n: int) -> list[float]:
    interval = binomtest(successes, n).proportion_ci(
        confidence_level=0.95,
        method="exact",
    )
    return [float(interval.low), float(interval.high)]


def _distribution(values: np.ndarray) -> dict:
    quantiles = {
        label: float(np.quantile(values, probability))
        for label, probability in (
            ("q00", 0.00),
            ("q05", 0.05),
            ("q25", 0.25),
            ("q50", 0.50),
            ("q75", 0.75),
            ("q95", 0.95),
            ("q99", 0.99),
            ("q100", 1.00),
        )
    }
    return {
        "mean": float(np.mean(values)),
        "sample_sd": float(np.std(values, ddof=1)),
        "nonzero_count": int(np.count_nonzero(values)),
        "nonzero_fraction": float(np.count_nonzero(values) / values.size),
        "quantiles": quantiles,
    }


def _load_rows(path: Path) -> list[dict]:
    if not path.is_file():
        raise EndpointReportError(f"missing null ledger: {path}")
    rows = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        1,
    ):
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise EndpointReportError(
                f"malformed null ledger row {line_number}"
            ) from exc
        if "error" in row:
            raise EndpointReportError(
                f"error record in null ledger row {line_number}"
            )
        rows.append(row)
    indices = [row.get("k") for row in rows]
    if len(indices) != len(set(indices)):
        raise EndpointReportError("duplicate mock indices in null ledger")
    if set(indices) != set(range(501)):
        raise EndpointReportError(
            "null ledger must contain exactly mock indices 0..500"
        )
    return rows


def compute_endpoints(rows: list[dict], observed_p_rip: float) -> dict:
    """Compute registered endpoints from validated rows.

    ``mock000`` is returned as a mechanism diagnostic and is excluded from all
    finite-null calculations.
    """
    by_k = {row["k"]: row for row in rows}
    if set(by_k) != set(range(501)) or len(rows) != 501:
        raise EndpointReportError("endpoint input must contain unique k=0..500")
    noisy = [by_k[k] for k in range(1, 501)]
    rip = np.asarray([row["P"]["RIP"] for row in noisy], dtype=float)
    heat = np.asarray([row["P_heat"] for row in noisy], dtype=float)
    other = np.asarray([row["P"]["OTHER"] for row in noisy], dtype=float)
    boundary = np.asarray(
        [row["boundary_fraction"] for row in noisy],
        dtype=float,
    )
    arrays = {
        "P_RIP": rip,
        "P_heat": heat,
        "OTHER": other,
        "boundary": boundary,
    }
    for label, values in arrays.items():
        if not np.all(np.isfinite(values)):
            raise EndpointReportError(f"{label} contains a non-finite value")
        if np.any(values < 0.0) or np.any(values > 1.0):
            raise EndpointReportError(f"{label} contains a value outside [0,1]")
    if not np.isfinite(observed_p_rip) or not 0.0 <= observed_p_rip <= 1.0:
        raise EndpointReportError("observed P_RIP is invalid")

    lower_mask = rip <= observed_p_rip
    lower_indices = [
        int(k) for k, selected in zip(range(1, 501), lower_mask) if selected
    ]
    lower_count = int(np.sum(lower_mask))
    direction_mask = heat > 0.5
    direction_indices = [
        int(k) for k, selected in zip(range(1, 501), direction_mask) if selected
    ]
    direction_count = int(np.sum(direction_mask))
    ks = kstest(heat, "uniform", method="exact")
    max_other_offset = int(np.argmax(other))
    max_boundary_offset = int(np.argmax(boundary))

    return {
        "observed": {
            "P_RIP": float(observed_p_rip),
        },
        "primary_depth": {
            "criterion": "P_RIP_mock <= P_RIP_observed",
            "K": lower_count,
            "N": 500,
            "fraction": float(lower_count / 500),
            "qualifying_mock_indices": lower_indices,
            "minimum_null_P_RIP": float(np.min(rip)),
            "minimum_null_mock_index": int(np.argmin(rip) + 1),
        },
        "finite_simulation_lower_tail": {
            "rule": "(K+1)/(N+1)",
            "numerator": lower_count + 1,
            "denominator": 501,
            "p_plus_one": float((lower_count + 1) / 501),
        },
        "tail_probability_interval": {
            "method": "two-sided exact 95% Clopper-Pearson",
            "confidence_level": 0.95,
            "interval": _exact_interval(lower_count, 500),
        },
        "direction": {
            "criterion": "P_heat > 0.5",
            "K": direction_count,
            "N": 500,
            "fraction": float(direction_count / 500),
            "exact_binomial_95_interval": _exact_interval(
                direction_count,
                500,
            ),
            "qualifying_mock_indices": direction_indices,
        },
        "uniformity_diagnostic": {
            "variable": "P_heat",
            "reference_distribution": "Uniform(0,1)",
            "test": "one-sample Kolmogorov-Smirnov, exact two-sided",
            "statistic": float(ks.statistic),
            "p_value": float(ks.pvalue),
        },
        "boundary_budget": {
            "OTHER": {
                "maximum": float(other[max_other_offset]),
                "maximum_mock_index": max_other_offset + 1,
                "distribution": _distribution(other),
            },
            "boundary_fraction": {
                "maximum": float(boundary[max_boundary_offset]),
                "maximum_mock_index": max_boundary_offset + 1,
                "distribution": _distribution(boundary),
            },
        },
        "mock000_mechanism_diagnostic_excluded_from_null": {
            "P_RIP": float(by_k[0]["P"]["RIP"]),
            "P_heat": float(by_k[0]["P_heat"]),
            "OTHER": float(by_k[0]["P"]["OTHER"]),
            "boundary_fraction": float(by_k[0]["boundary_fraction"]),
        },
    }


def build_report(
    run_root: Path = DEFAULT_RUN_ROOT,
    observed_path: Path = DEFAULT_OBSERVED,
) -> dict:
    run_root = Path(run_root).resolve()
    observed_path = Path(observed_path).resolve()
    ledger = run_root / "results.jsonl"
    completion = run_root / "completion_audit.json"
    if not completion.is_file():
        raise EndpointReportError("completion audit is missing")
    completion_payload = json.loads(completion.read_text(encoding="utf-8"))
    if completion_payload.get("status") != "PASS":
        raise EndpointReportError("completion audit did not pass")
    observed = json.loads(observed_path.read_text(encoding="utf-8"))
    endpoints = compute_endpoints(
        _load_rows(ledger),
        float(observed["RIP"]["P"]),
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS",
        "protocol_endpoint_source": "plan/PRD_EXTENSION_PROTOCOL.md section 5.2",
        "inputs": {
            "results_ledger": {
                "path": str(ledger.relative_to(ROOT)),
                "sha256": _sha256(ledger),
            },
            "completion_audit": {
                "path": str(completion.relative_to(ROOT)),
                "sha256": _sha256(completion),
                "status": completion_payload["status"],
            },
            "observed_fate": {
                "path": str(observed_path.relative_to(ROOT)),
                "sha256": _sha256(observed_path),
            },
        },
        "methods": {
            "scipy_version": scipy.__version__,
            "quantile_method": "numpy default linear",
            "mock000_included_in_null": False,
            "early_stopping": False,
        },
        "endpoints": endpoints,
    }


def _atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        delete=False,
    ) as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
        temporary = Path(handle.name)
    os.replace(temporary, path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, default=DEFAULT_RUN_ROOT)
    parser.add_argument("--observed", type=Path, default=DEFAULT_OBSERVED)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    output = args.output or args.run_root / "endpoints.json"
    report = build_report(args.run_root, args.observed)
    _atomic_json(output, report)
    endpoint = report["endpoints"]
    print(
        json.dumps(
            {
                "status": report["status"],
                "output": str(output),
                "K_over_N": [
                    endpoint["primary_depth"]["K"],
                    endpoint["primary_depth"]["N"],
                ],
                "p_plus_one": endpoint[
                    "finite_simulation_lower_tail"
                ]["p_plus_one"],
                "direction_K_over_N": [
                    endpoint["direction"]["K"],
                    endpoint["direction"]["N"],
                ],
                "KS_p": endpoint["uniformity_diagnostic"]["p_value"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
