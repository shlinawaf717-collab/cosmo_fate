#!/usr/bin/env python3
"""Read-only 20-D convergence diagnostics for one WP5 smoothing width."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

import numpy as np

from pipeline import monitor_wp4_f0 as base


ROOT = Path(__file__).resolve().parents[1]
SAMPLED_PARAMETERS = (
    "logA", "ns", "theta_MC_100", "ombh2", "omch2", "tau",
    "w1", "w2", "w3", "w4", "Mb", "A_planck", "amp_143", "amp_217",
    "amp_143x217", "n_143", "n_217", "n_143x217", "calTE", "calEE",
)
WIDTH_TAGS = ("0p005", "0p01", "0p02")
BIN_PARAMETERS = ("w1", "w2", "w3", "w4")


def chain_paths(width_tag: str, root: Path | None = None) -> tuple[Path, ...]:
    if width_tag not in WIDTH_TAGS:
        raise ValueError(f"unknown WP5 width tag: {width_tag}")
    root = root or ROOT / "runs/prd_extension/wp5_bin4/production_system"
    return tuple(root / f"delta_{width_tag}/c{i}/chain.1.txt" for i in range(1, 5))


def collect(paths: Sequence[Path], burns=(0.2, 0.5, 0.7), primary=0.5) -> dict:
    """Collect WP5 diagnostics without inheriting WP4's ``w``/``wa`` gates.

    The numerical estimators are intentionally shared with the audited WP4
    monitor. The payload assembly is local because WP4's convenience wrapper
    also assembles model-specific gates for the CPL parameters ``w`` and
    ``wa``. Reusing that wrapper made a valid WP5 diagnostic crash after the
    first four chains became readable.
    """
    started = base._utc_now()
    snapshots = [base.snapshot_chain(path) for path in paths]
    if any(snapshot.columns != snapshots[0].columns for snapshot in snapshots[1:]):
        raise ValueError("chain headers differ")

    original = base.SAMPLED_PARAMETERS
    base.SAMPLED_PARAMETERS = SAMPLED_PARAMETERS
    try:
        rminus1 = {
            f"{burn:.1f}": base.cobaya_multivariate_rminus1(snapshots, burn)
            for burn in burns
        }
        bulk, tail, equalized_draws = base.rank_normalized_ess(snapshots, primary)
    finally:
        base.SAMPLED_PARAMETERS = original

    gates = {
        "rminus1_20d_burn_0p5_lt_0p01": rminus1["0.5"] < 0.01,
        "bulk_ess_all_wbins_gt_1000": all(bulk[name] > 1000 for name in BIN_PARAMETERS),
        "tail_ess_all_wbins_gt_400": all(tail[name] > 400 for name in BIN_PARAMETERS),
    }
    return {
        "schema_version": "wp5-bin4-read-only-monitor-v2",
        "captured_at_start_utc": started,
        "captured_at_end_utc": base._utc_now(),
        "decision_authority": False,
        "sampler_signal_capability": False,
        "status": "CANDIDATE_PASS" if all(gates.values()) else "CANDIDATE_CONTINUE",
        "chain_snapshots": [
            {
                "path": snapshot.path,
                "rows": int(snapshot.data.shape[0]),
                "total_weight": int(
                    np.rint(snapshot.data[:, snapshot.columns.index("weight")]).sum()
                ),
                "captured_bytes": snapshot.captured_bytes,
                "file_size_at_open": snapshot.file_size_at_open,
                "mtime_ns_at_open": snapshot.mtime_ns_at_open,
                "sha256": snapshot.sha256,
            }
            for snapshot in snapshots
        ],
        "rminus1": {
            "definition": "Cobaya 3.6.2 MPI-chain multivariate, 20 WP5 sampled parameters",
            "by_burn_fraction": rminus1,
        },
        "ess": {
            "definition": "rank-normalized split bulk ESS and binary 5%/95% tail ESS",
            "primary_burn_fraction": primary,
            "equalized_split_draws_total": equalized_draws,
            "bulk_by_parameter": bulk,
            "tail_by_parameter": tail,
        },
        "candidate_gates": gates,
        "blinding": {
            "posterior_locations_reported": False,
            "posterior_intervals_reported": False,
            "best_fit_reported": False,
            "likelihood_values_reported": False,
            "fate_quantities_reported": False,
        },
    }


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
