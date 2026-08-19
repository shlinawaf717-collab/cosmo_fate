#!/usr/bin/env python3
"""Read-only 18-D convergence monitor for the WSL2 F1 chain set."""

from __future__ import annotations

import json
from pathlib import Path

from payload.pipeline import monitor_wp4_f0 as base


ROOT = Path(__file__).resolve().parents[1]
SAMPLED_PARAMETERS = (
    "logA", "ns", "theta_MC_100", "ombh2", "omch2", "tau", "w", "wa", "Mb",
    "A_planck", "amp_143", "amp_217", "amp_143x217", "n_143", "n_217",
    "n_143x217", "calTE", "calEE",
)
CHAIN_PATHS = tuple(ROOT / f"work/f1/c{i}/chain.1.txt" for i in range(1, 5))


def collect(chain_paths=CHAIN_PATHS, burns=(0.2, 0.5, 0.7), primary=0.5) -> dict:
    original = base.SAMPLED_PARAMETERS
    base.SAMPLED_PARAMETERS = SAMPLED_PARAMETERS
    try:
        payload = base.collect_diagnostics(chain_paths, burn_fractions=burns, primary_burn=primary)
    finally:
        base.SAMPLED_PARAMETERS = original
    payload["schema_version"] = "wp4-f1-wsl2-read-only-monitor-v1"
    payload["rminus1"]["definition"] = "Cobaya 3.6.2 MPI-chain multivariate, 18 F1 sampled parameters"
    payload["candidate_gates"] = {
        "rminus1_18d_burn_0p5_lt_0p01": payload["rminus1"]["by_burn_fraction"]["0.5"] < 0.01,
        "bulk_ess_w_wa_gt_1000": min(payload["ess"]["bulk_by_parameter"][name] for name in ("w", "wa")) > 1000,
        "tail_ess_w_wa_gt_400": min(payload["ess"]["tail_by_parameter"][name] for name in ("w", "wa")) > 400,
    }
    payload["status"] = "CANDIDATE_PASS" if all(payload["candidate_gates"].values()) else "CANDIDATE_CONTINUE"
    return payload


if __name__ == "__main__":
    payload = collect()
    print(json.dumps({
        "status": payload["status"],
        "rows": [item["rows"] for item in payload["chain_snapshots"]],
        "rminus1": payload["rminus1"]["by_burn_fraction"],
        "bulk_ess_w_wa": {name: payload["ess"]["bulk_by_parameter"][name] for name in ("w", "wa")},
        "tail_ess_w_wa": {name: payload["ess"]["tail_by_parameter"][name] for name in ("w", "wa")},
        "chain_sha256": [item["sha256"] for item in payload["chain_snapshots"]],
    }, indent=2, sort_keys=True))
