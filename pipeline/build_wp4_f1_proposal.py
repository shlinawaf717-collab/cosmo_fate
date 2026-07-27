#!/usr/bin/env python3
"""Build the WP4 F1 proposal covariance from converged F0 tail halves.

The builder refuses to run before the audited F0 external stop has completed.
It records covariance structure and integrity metadata but no posterior
location, likelihood, model-comparison, or fate quantity.
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

import numpy as np

from pipeline.monitor_wp4_f0 import (
    DEFAULT_CHAIN_PATHS,
    SAMPLED_PARAMETERS,
    snapshot_chain,
)


ROOT = Path(__file__).resolve().parents[1]
WP4_ROOT = ROOT / "runs/prd_extension/wp4_full_cmb"
DEFAULT_CLOSURE_AUDIT = (
    WP4_ROOT / "f0/external_monitor/final_stop_audit.json"
)
DEFAULT_OUTPUT = WP4_ROOT / "f1_proposal.covmat"
DEFAULT_AUDIT = WP4_ROOT / "f1_proposal_audit.json"
SCHEMA_VERSION = "wp4-f1-proposal-from-f0-v1"
BURN_FRACTION = 0.5
RELATIVE_EIGENVALUE_FLOOR = 1e-12


class F1ProposalError(RuntimeError):
    """Raised when F0 is not closed or its proposal inputs are invalid."""


def validate_f0_closure(path: Path) -> dict:
    if not path.is_file():
        raise F1ProposalError(f"F0 closure audit is missing: {path}")
    audit = json.loads(path.read_text(encoding="utf-8"))
    if not str(audit.get("status", "")).startswith("EXTERNALLY_STOPPED"):
        raise F1ProposalError(f"F0 is not externally stopped: {audit.get('status')}")
    if audit.get("post_termination_gates_pass") is not True:
        raise F1ProposalError("F0 post-termination convergence gates did not pass")
    return audit


def proposal_from_tail_halves(
    chain_paths: list[Path],
    parameters: tuple[str, ...] = SAMPLED_PARAMETERS,
    burn_fraction: float = BURN_FRACTION,
) -> tuple[np.ndarray, dict]:
    pooled_values = []
    pooled_weights = []
    records = []
    for path in chain_paths:
        snapshot = snapshot_chain(path)
        index = {name: i for i, name in enumerate(snapshot.columns)}
        missing = set(("weight", *parameters)).difference(index)
        if missing:
            raise F1ProposalError(f"{path} lacks columns {sorted(missing)}")
        first = int(snapshot.data.shape[0] * burn_fraction)
        selected = snapshot.data[first:]
        weights_raw = selected[:, index["weight"]]
        weights = np.rint(weights_raw).astype(np.int64)
        if np.any(weights <= 0) or not np.allclose(weights_raw, weights):
            raise F1ProposalError(f"{path} has invalid integer weights")
        values = selected[:, [index[name] for name in parameters]]
        if np.any(~np.isfinite(values)):
            raise F1ProposalError(f"{path} has non-finite proposal values")
        pooled_values.append(values)
        pooled_weights.append(weights)
        records.append(
            {
                "path": str(path),
                "captured_prefix_sha256": snapshot.sha256,
                "complete_rows": int(snapshot.data.shape[0]),
                "post_burn_rows": int(selected.shape[0]),
                "post_burn_weight": int(weights.sum()),
            }
        )
    values = np.concatenate(pooled_values, axis=0)
    weights = np.concatenate(pooled_weights)
    covariance = np.atleast_2d(
        np.cov(values.T, ddof=0, fweights=weights)
    )
    covariance = 0.5 * (covariance + covariance.T)
    raw_eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    maximum = float(raw_eigenvalues[-1])
    floor = maximum * RELATIVE_EIGENVALUE_FLOOR
    floored_eigenvalues = np.maximum(raw_eigenvalues, floor)
    regularized = bool(np.any(floored_eigenvalues != raw_eigenvalues))
    if regularized:
        covariance = (
            eigenvectors
            @ np.diag(floored_eigenvalues)
            @ eigenvectors.T
        )
        covariance = 0.5 * (covariance + covariance.T)
    np.linalg.cholesky(covariance)
    final_eigenvalues = np.linalg.eigvalsh(covariance)
    audit = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "role": "F1 proposal efficiency only; posterior target is unchanged",
        "source": "complete F0 chain prefixes after 50% row burn-in",
        "parameters": list(parameters),
        "row_burn_fraction": burn_fraction,
        "integer_weights_used": True,
        "posterior_locations_reported": False,
        "likelihood_values_reported": False,
        "fate_quantities_reported": False,
        "relative_eigenvalue_floor": RELATIVE_EIGENVALUE_FLOOR,
        "regularization_applied": regularized,
        "raw_minimum_eigenvalue": float(raw_eigenvalues[0]),
        "final_minimum_eigenvalue": float(final_eigenvalues[0]),
        "maximum_eigenvalue": float(final_eigenvalues[-1]),
        "condition_number": float(
            final_eigenvalues[-1] / final_eigenvalues[0]
        ),
        "post_burn_weight": int(weights.sum()),
        "chains": records,
    }
    return covariance, audit


def _atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
        temporary = Path(handle.name)
    os.replace(temporary, path)


def _write_covariance(path: Path, covariance: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(dir=path.parent)
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        np.savetxt(
            temporary,
            covariance,
            header=" ".join(SAMPLED_PARAMETERS),
            comments="# ",
        )
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--closure-audit", type=Path, default=DEFAULT_CLOSURE_AUDIT
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    args = parser.parse_args()
    closure = validate_f0_closure(args.closure_audit)
    covariance, audit = proposal_from_tail_halves(
        [ROOT / path for path in DEFAULT_CHAIN_PATHS]
    )
    _write_covariance(args.output, covariance)
    from pipeline.evaluate_wp4_f0_external_stop import sha256_file

    audit["f0_closure_audit"] = {
        "path": str(args.closure_audit),
        "sha256": sha256_file(args.closure_audit),
        "status": closure["status"],
    }
    audit["covariance"] = {
        "path": str(args.output),
        "sha256": sha256_file(args.output),
    }
    _atomic_json(args.audit, audit)
    print(
        json.dumps(
            {
                "status": audit["status"],
                "output": str(args.output),
                "condition_number": audit["condition_number"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
