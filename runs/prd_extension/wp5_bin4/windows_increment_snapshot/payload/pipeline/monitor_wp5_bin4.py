#!/usr/bin/env python3
"""Read-only 20-D convergence diagnostics for one WP5 smoothing width."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from pipeline import monitor_wp4_f0 as base


ROOT = Path(__file__).resolve().parents[1]
SAMPLED_PARAMETERS = (
    "logA", "ns", "theta_MC_100", "ombh2", "omch2", "tau",
    "w1", "w2", "w3", "w4", "Mb", "A_planck", "amp_143", "amp_217",
    "amp_143x217", "n_143", "n_217", "n_143x217", "calTE", "calEE",
)
WIDTH_TAGS = ("0p005", "0p01", "0p02")


def chain_paths(width_tag: str, root: Path | None = None) -> tuple[Path, ...]:
    if width_tag not in WIDTH_TAGS:
        raise ValueError(f"unknown WP5 width tag: {width_tag}")
    root = root or ROOT / "runs/prd_extension/wp5_bin4/production_system"
    return tuple(root / f"delta_{width_tag}/c{i}/chain.1.txt" for i in range(1, 5))


def collect(paths: Sequence[Path], burns=(0.2, 0.5, 0.7), primary=0.5) -> dict:
    original = base.SAMPLED_PARAMETERS
    base.SAMPLED_PARAMETERS = SAMPLED_PARAMETERS
    try:
        payload = base.collect_diagnostics(paths, burn_fractions=burns, primary_burn=primary)
    finally:
        base.SAMPLED_PARAMETERS = original
    payload["schema_version"] = "wp5-bin4-read-only-monitor-v1"
    payload["rminus1"]["definition"] = (
        "Cobaya 3.6.2 MPI-chain multivariate, 20 WP5 sampled parameters"
    )
    payload["candidate_gates"] = {
        "rminus1_20d_burn_0p5_lt_0p01": payload["rminus1"]["by_burn_fraction"]["0.5"] < 0.01,
        "bulk_ess_all_wbins_gt_1000": all(
            payload["ess"]["bulk_by_parameter"][name] > 1000
            for name in ("w1", "w2", "w3", "w4")
        ),
        "tail_ess_all_wbins_gt_400": all(
            payload["ess"]["tail_by_parameter"][name] > 400
            for name in ("w1", "w2", "w3", "w4")
        ),
    }
    payload["status"] = "CANDIDATE_PASS" if all(payload["candidate_gates"].values()) else "CANDIDATE_CONTINUE"
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("width_tag", choices=WIDTH_TAGS)
    parser.add_argument("--chain", action="append", type=Path, dest="chains")
    args = parser.parse_args(); paths = tuple(args.chains or chain_paths(args.width_tag))
    payload = collect(paths)
    print(json.dumps({
        "status": payload["status"],
        "rows": [row["rows"] for row in payload["chain_snapshots"]],
        "rminus1": payload["rminus1"]["by_burn_fraction"],
        "bulk_ess_wbins": {name: payload["ess"]["bulk_by_parameter"][name] for name in ("w1","w2","w3","w4")},
        "tail_ess_wbins": {name: payload["ess"]["tail_by_parameter"][name] for name in ("w1","w2","w3","w4")},
        "chain_sha256": [row["sha256"] for row in payload["chain_snapshots"]],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__": raise SystemExit(main())
