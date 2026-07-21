#!/usr/bin/env python3
"""Aggregate independent D0 nested runs without pooling internal logZ errors."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

try:
    from pipeline import nested_core as nc
except ModuleNotFoundError:  # pragma: no cover - direct script invocation
    import nested_core as nc


def aggregate(payloads: list[dict], sources: list[str] | None = None) -> dict:
    if len(payloads) < 2:
        raise ValueError("at least two independent seed runs are required")
    seeds = [int(row["seed"]) for row in payloads]
    if len(set(seeds)) != len(seeds):
        raise ValueError("seed runs must be unique")
    fate = np.array([
        [row["P_fate_weighted"][label] for label in nc.FATE_LABELS]
        for row in payloads
    ], dtype=float)
    fate_mean = fate.mean(axis=0)
    fate_mean[-1] += 1.0 - float(fate_mean.sum())
    fate_dict = dict(zip(nc.FATE_LABELS, map(float, fate_mean)))

    lnb = np.array([row["lnB_CPL_over_LCDM"] for row in payloads], dtype=float)
    lnz_cpl = np.array([row["lnZ_CPL"] for row in payloads], dtype=float)
    lnz_lcdm = np.array([row["lnZ_LCDM"] for row in payloads], dtype=float)
    internal = np.array([row["lnB_err"] for row in payloads], dtype=float)
    rip = fate[:, nc.FATE_LABELS.index("RIP")]

    out = {
        "schema_version": "nested-multiseed-aggregate-v1",
        "source_schema_version": nc.SCHEMA_VERSION,
        "seeds": seeds,
        "n_independent_runs": len(payloads),
        "source_files": sources,
        "headline_fate_estimator": "mean across independent normalized-original-logwt runs",
        "P_fate_weighted": fate_dict,
        "P_fate_nested": fate_dict,
        "P_fate_between_seed_sd": dict(zip(
            nc.FATE_LABELS, map(float, fate.std(axis=0, ddof=1))
        )),
        "P_RIP_range": [float(rip.min()), float(rip.max())],
        "P_RIP_se_binom": None,
        "lnZ_CPL": float(lnz_cpl.mean()),
        "lnZ_LCDM": float(lnz_lcdm.mean()),
        "lnB_CPL_over_LCDM": float(lnb.mean()),
        "lnB_between_seed_sd": float(lnb.std(ddof=1)),
        "lnB_range": [float(lnb.min()), float(lnb.max())],
        "per_run_internal_lnB_errors": list(map(float, internal)),
        "uncertainty_note": (
            "Between-seed standard deviations describe run-to-run nested variation. "
            "Per-run internal dynesty logZ errors remain separate and are not pooled "
            "as if they were independent measurements of one random quantity."
        ),
        "runs": [
            {
                "seed": int(row["seed"]),
                "P_RIP_weighted": float(row["P_fate_weighted"]["RIP"]),
                "lnB_CPL_over_LCDM": float(row["lnB_CPL_over_LCDM"]),
                "lnB_internal_error": float(row["lnB_err"]),
                "CPL_ess": float(row["CPL_audit"]["ess"]),
                "LCDM_ess": float(row["LCDM_audit"]["ess"]),
            }
            for row in payloads
        ],
    }
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payloads = [json.loads(path.read_text(encoding="utf-8")) for path in args.inputs]
    out = aggregate(payloads, [str(path) for path in args.inputs])
    nc.atomic_write_json(str(args.output), out, indent=1)
    print(f"wrote {args.output}")
    print(
        f"P(RIP)={out['P_fate_weighted']['RIP']:.6g} "
        f"+-{out['P_fate_between_seed_sd']['RIP']:.2g} between seeds; "
        f"lnB={out['lnB_CPL_over_LCDM']:.3f} "
        f"+-{out['lnB_between_seed_sd']:.3f} between seeds"
    )


if __name__ == "__main__":
    main()
