#!/usr/bin/env python3
"""Derive the WP4 F0 proposal covariance from archived official chains.

The covariance changes sampling efficiency only.  It does not alter the
likelihood, priors, scientific endpoints, or fate classifier.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import yaml

from pipeline.wp4_preflight import (
    OFFICIAL_CHAIN_HASHES,
    OFFICIAL_ROOT,
    ROOT,
    WP4PreflightError,
    WP4_ROOT,
    _chain_header,
    display_path,
    sha256_file,
)


DEFAULT_OUTPUT = WP4_ROOT / "f0_proposal.covmat"
DEFAULT_AUDIT = WP4_ROOT / "f0_proposal_audit.json"
OFFICIAL_CONFIG = OFFICIAL_ROOT / "chain.updated.yaml"


def sampled_parameters(config_path: Path = OFFICIAL_CONFIG) -> list[str]:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    return [
        name
        for name, definition in config["params"].items()
        if isinstance(definition, dict) and "prior" in definition
    ]


def proposal_covariance(
    chain_paths: list[Path] | None = None,
    parameters: list[str] | None = None,
    expected_hashes: dict[str, str] | None = None,
) -> tuple[np.ndarray, dict]:
    paths = chain_paths or [
        OFFICIAL_ROOT / name for name in sorted(OFFICIAL_CHAIN_HASHES)
    ]
    names = sampled_parameters() if parameters is None else parameters
    hashes = OFFICIAL_CHAIN_HASHES if expected_hashes is None else expected_hashes
    total_weight = 0.0
    first_moment = np.zeros(len(names))
    second_moment = np.zeros((len(names), len(names)))
    records = []
    for path in paths:
        digest = sha256_file(path)
        expected = hashes.get(path.name)
        if expected is not None and digest != expected:
            raise WP4PreflightError(f"official chain hash mismatch: {path.name}")
        header = _chain_header(path)
        absent = [name for name in ("weight", *names) if name not in header]
        if absent:
            raise WP4PreflightError(f"{path.name} lacks proposal columns {absent}")
        usecols = [header.index("weight"), *[header.index(name) for name in names]]
        table = np.loadtxt(path, comments="#", usecols=usecols, ndmin=2)
        weights = table[:, 0]
        values = table[:, 1:]
        if np.any(~np.isfinite(table)) or np.any(weights <= 0):
            raise WP4PreflightError(f"invalid chain data: {path.name}")
        chain_weight = float(weights.sum())
        total_weight += chain_weight
        first_moment += np.einsum("i,ij->j", weights, values)
        second_moment += np.einsum("i,ij,ik->jk", weights, values, values)
        records.append(
            {
                "path": display_path(path),
                "sha256": digest,
                "raw_rows": int(table.shape[0]),
                "posterior_weight": chain_weight,
            }
        )

    mean = first_moment / total_weight
    covariance = second_moment / total_weight - np.outer(mean, mean)
    covariance = 0.5 * (covariance + covariance.T)
    eigenvalues = np.linalg.eigvalsh(covariance)
    if eigenvalues[0] <= 0:
        raise WP4PreflightError(
            f"proposal covariance is not positive definite: min={eigenvalues[0]}"
        )
    audit = {
        "schema_version": "wp4-f0-proposal-v1",
        "status": "PASS",
        "role": "proposal efficiency only; posterior target is unchanged",
        "sampling_performed": False,
        "fate_calculation_performed": False,
        "parameters": names,
        "means": {name: float(value) for name, value in zip(names, mean)},
        "standard_deviations": {
            name: float(value)
            for name, value in zip(names, np.sqrt(np.diag(covariance)))
        },
        "minimum_eigenvalue": float(eigenvalues[0]),
        "maximum_eigenvalue": float(eigenvalues[-1]),
        "condition_number": float(eigenvalues[-1] / eigenvalues[0]),
        "posterior_weight": total_weight,
        "chains": records,
    }
    return covariance, audit


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    args = parser.parse_args(argv)
    covariance, audit = proposal_covariance()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    np.savetxt(
        args.output,
        covariance,
        header=" ".join(audit["parameters"]),
        comments="# ",
    )
    audit["covariance"] = {
        "path": str(args.output.relative_to(ROOT)),
        "sha256": sha256_file(args.output),
    }
    args.audit.write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        f"PASS: wrote {args.output}; "
        f"condition_number={audit['condition_number']:.6g}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
