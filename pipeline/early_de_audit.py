#!/usr/bin/env python3
"""Audit archived BIN4 posterior mass against the A-006 early-DE hard gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

try:
    from pipeline.classify_fparam import load_release_columns
    from pipeline.wparams import EARLY_DE_MAX_RATIO, Z_EARLY_DE_GATE, bin4_early_de_ratio
except ModuleNotFoundError:  # pragma: no cover
    from classify_fparam import load_release_columns
    from wparams import EARLY_DE_MAX_RATIO, Z_EARLY_DE_GATE, bin4_early_de_ratio

ROOT = Path(__file__).resolve().parents[1]


def weighted_quantile(values, weights, quantiles):
    order = np.argsort(values)
    values = np.asarray(values)[order]
    weights = np.asarray(weights, dtype=float)[order]
    cdf = np.cumsum(weights) / weights.sum()
    return np.interp(quantiles, cdf, values)


def compute(root: str, z_check=Z_EARLY_DE_GATE, max_ratio=EARLY_DE_MAX_RATIO) -> dict:
    columns, weights = load_release_columns(
        root, ["omegam", "H0", "w1", "w2", "w3", "w4"]
    )
    ratio = bin4_early_de_ratio(
        columns["omegam"], columns["H0"], columns["w1"], columns["w2"],
        columns["w3"], columns["w4"], z=z_check,
    )
    weights = np.asarray(weights, dtype=float)
    weights /= weights.sum()
    fail = ratio >= max_ratio
    quantiles = weighted_quantile(ratio, weights, [0.5, 0.95, 0.99, 0.999])
    root_path = Path(root).resolve()
    try:
        displayed_root = str(root_path.relative_to(ROOT))
    except ValueError:
        displayed_root = str(root_path)
    return {
        "schema_version": "early-de-audit-v1-a006",
        "chain_root": displayed_root,
        "z_check": float(z_check),
        "hard_gate": "rho_DE/rho_m < max_ratio",
        "max_ratio": float(max_ratio),
        "n_post_burn_samples": int(len(ratio)),
        "weighted_failure_fraction": float(weights[fail].sum()),
        "n_failing_rows": int(np.count_nonzero(fail)),
        "weighted_quantiles": dict(zip(
            ("q50", "q95", "q99", "q999"), map(float, quantiles)
        )),
        "maximum_row_ratio": float(np.max(ratio)),
        "decision": "PASS" if not np.any(fail) else "REFIT_REQUIRED",
        "scope": "post-hoc validity audit of archived compressed-CMB-conditioned BIN4 chains",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT / "runs/phase3/fparam/bin4"))
    parser.add_argument("--output", type=Path,
                        default=ROOT / "runs/phase3/fparam/early_de_audit.json")
    args = parser.parse_args()
    out = compute(args.root)
    args.output.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.output}: {out['decision']}, failures={out['weighted_failure_fraction']:.3g}")


if __name__ == "__main__":
    main()
