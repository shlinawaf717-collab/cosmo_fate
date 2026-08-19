#!/usr/bin/env python3
"""Build a block-diagonal efficiency proposal for 20-D WP5 BIN4 sampling."""

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np

from pipeline.audit_wp4_f0_reproduction import atomic_write_json, sha256_file


ROOT = Path(__file__).resolve().parents[1]
F1_RAW = ROOT / "runs/prd_extension/wp4_full_cmb/f1_wsl2/raw/work/f1"
ARCHIVED_BIN4 = ROOT / "runs/phase3/fparam"
OUTPUT = ROOT / "runs/prd_extension/wp5_bin4/proposal.covmat"
AUDIT = ROOT / "runs/prd_extension/wp5_bin4/proposal_audit.json"
PARAMETERS = (
    "logA", "ns", "theta_MC_100", "ombh2", "omch2", "tau",
    "w1", "w2", "w3", "w4", "Mb", "A_planck", "amp_143", "amp_217",
    "amp_143x217", "n_143", "n_217", "n_143x217", "calTE", "calEE",
)
SHARED = tuple(name for name in PARAMETERS if name not in {"w1", "w2", "w3", "w4"})
W_BINS = ("w1", "w2", "w3", "w4")


class WP5ProposalError(RuntimeError):
    """Raised when the proposal source chains cannot be audited."""


def read_chains(paths: list[Path], burn: float) -> tuple[list[str], np.ndarray, np.ndarray, list[dict]]:
    arrays = []; weights = []; header = None; records = []
    for path in paths:
        with path.open(encoding="utf-8") as stream:
            columns = stream.readline().lstrip("#").split()
        if header is None: header = columns
        if columns != header: raise WP5ProposalError("proposal source headers differ")
        data = np.loadtxt(path, comments="#", ndmin=2)
        post = data[int(burn * len(data)):]
        arrays.append(post); weights.append(post[:, columns.index("weight")])
        records.append({"path": str(path.relative_to(ROOT)), "sha256": sha256_file(path),
                        "full_rows": len(data), "post_burn_rows": len(post),
                        "post_burn_weight": int(np.rint(weights[-1]).sum())})
    return header, np.concatenate(arrays), np.concatenate(weights), records


def weighted_covariance(columns: list[str], data: np.ndarray, weights: np.ndarray,
                        names: tuple[str, ...]) -> np.ndarray:
    missing = set(names).difference(columns)
    if missing: raise WP5ProposalError(f"proposal source missing {sorted(missing)}")
    integer = np.rint(weights).astype(np.int64)
    if np.any(integer <= 0) or not np.allclose(weights, integer):
        raise WP5ProposalError("proposal weights are not positive integers")
    values = data[:, [columns.index(name) for name in names]]
    return np.cov(values.T, ddof=0, fweights=integer)


def build() -> dict:
    f1_paths = [F1_RAW / f"c{i}/chain.1.txt" for i in range(1, 5)]
    bin4_paths = [path for path in sorted(ARCHIVED_BIN4.glob("bin4_*.txt"))
                  if path.name.split(".")[-2].isdigit()]
    f1_columns, f1_data, f1_weights, f1_records = read_chains(f1_paths, 0.5)
    b_columns, b_data, b_weights, b_records = read_chains(bin4_paths, 0.3)
    shared = weighted_covariance(f1_columns, f1_data, f1_weights, SHARED)
    bins = weighted_covariance(b_columns, b_data, b_weights, W_BINS)
    matrix = np.zeros((len(PARAMETERS), len(PARAMETERS)))
    shared_index = [PARAMETERS.index(name) for name in SHARED]
    bin_index = [PARAMETERS.index(name) for name in W_BINS]
    matrix[np.ix_(shared_index, shared_index)] = shared
    matrix[np.ix_(bin_index, bin_index)] = bins
    eigenvalues = np.linalg.eigvalsh(matrix)
    if eigenvalues.min() <= 0 or not np.all(np.isfinite(eigenvalues)):
        raise WP5ProposalError("combined WP5 proposal is not positive definite")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT.with_name(f".{OUTPUT.name}.tmp-{os.getpid()}")
    np.savetxt(temporary, matrix, header=" ".join(PARAMETERS)); os.replace(temporary, OUTPUT)
    scales = np.sqrt(np.diag(matrix))
    correlation = matrix / np.outer(scales, scales)
    payload = {
        "schema_version": "wp5-bin4-proposal-audit-v1", "status": "PASS",
        "role": "sampling efficiency only; block-diagonal construction does not change target",
        "parameters": list(PARAMETERS), "shape": list(matrix.shape),
        "sha256": sha256_file(OUTPUT), "minimum_eigenvalue": float(eigenvalues.min()),
        "maximum_eigenvalue": float(eigenvalues.max()),
        "condition_number": float(eigenvalues.max() / eigenvalues.min()),
        "correlation_condition_number": float(np.linalg.cond(correlation)),
        "cross_block_policy": "all F1-shared versus archived-BIN4-node covariances fixed to zero",
        "sources": {"F1_full_likelihood": f1_records, "archived_compressed_BIN4": b_records},
        "burn_fractions": {"F1": 0.5, "archived_BIN4": 0.3},
        "scientific_endpoint_generated": False,
    }
    atomic_write_json(AUDIT, payload); return payload


def main() -> int:
    payload = build(); print(json.dumps({"status": payload["status"],
                                         "condition_number": payload["condition_number"],
                                         "output": str(OUTPUT)})); return 0


if __name__ == "__main__": raise SystemExit(main())
