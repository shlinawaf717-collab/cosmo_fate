#!/usr/bin/env python3
"""Read-only convergence diagnostics for the WP4 F1 production chains."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Sequence

from pipeline import monitor_wp4_f0 as _f0_statistics


SCHEMA_VERSION = "wp4-f1-read-only-monitor-v1"
SAMPLED_PARAMETERS = (
    "logA", "ns", "theta_MC_100", "ombh2", "omch2", "tau", "w", "wa", "Mb",
    "A_planck", "amp_143", "amp_217", "amp_143x217", "n_143", "n_217",
    "n_143x217", "calTE", "calEE",
)
DEFAULT_CHAIN_PATHS = tuple(
    Path(f"runs/prd_extension/wp4_full_cmb/f1/c{i}/chain.1.txt")
    for i in range(1, 5)
)
DEFAULT_BURNS = (0.2, 0.5, 0.7)
PRIMARY_BURN = 0.5


def collect_diagnostics(
    chain_paths: Sequence[Path],
    burn_fractions: Sequence[float] = DEFAULT_BURNS,
    primary_burn: float = PRIMARY_BURN,
) -> dict:
    """Use the frozen F0 algorithms with F1's declared 18-D parameter set."""
    original = _f0_statistics.SAMPLED_PARAMETERS
    _f0_statistics.SAMPLED_PARAMETERS = SAMPLED_PARAMETERS
    try:
        payload = _f0_statistics.collect_diagnostics(
            chain_paths, burn_fractions=burn_fractions, primary_burn=primary_burn
        )
    finally:
        _f0_statistics.SAMPLED_PARAMETERS = original
    payload["schema_version"] = SCHEMA_VERSION
    payload["rminus1"]["definition"] = (
        "Cobaya 3.6.2 MPI-chain multivariate, 18 F1 sampled parameters"
    )
    payload["candidate_gates"] = {
        "rminus1_18d_burn_0p5_lt_0p01": (
            payload["rminus1"]["by_burn_fraction"]["0.5"] < 0.01
        ),
        "bulk_ess_w_wa_gt_1000": min(
            payload["ess"]["bulk_by_parameter"]["w"],
            payload["ess"]["bulk_by_parameter"]["wa"],
        ) > 1000,
        "tail_ess_w_wa_gt_400": min(
            payload["ess"]["tail_by_parameter"]["w"],
            payload["ess"]["tail_by_parameter"]["wa"],
        ) > 400,
    }
    payload["status"] = (
        "CANDIDATE_PASS" if all(payload["candidate_gates"].values())
        else "CANDIDATE_CONTINUE"
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chain", action="append", type=Path, dest="chains")
    parser.add_argument("--watch-seconds", type=float)
    args = parser.parse_args()
    chains = tuple(args.chains or DEFAULT_CHAIN_PATHS)
    while True:
        payload = collect_diagnostics(chains)
        print(json.dumps({
            "status": payload["status"],
            "rows": [item["rows"] for item in payload["chain_snapshots"]],
            "rminus1": payload["rminus1"]["by_burn_fraction"],
            "bulk_ess_w_wa": {
                key: payload["ess"]["bulk_by_parameter"][key] for key in ("w", "wa")
            },
            "tail_ess_w_wa": {
                key: payload["ess"]["tail_by_parameter"][key] for key in ("w", "wa")
            },
            "candidate_gates": payload["candidate_gates"],
            "chain_sha256": [item["sha256"] for item in payload["chain_snapshots"]],
        }, indent=2, sort_keys=True), flush=True)
        if args.watch_seconds is None:
            return 0
        time.sleep(args.watch_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
