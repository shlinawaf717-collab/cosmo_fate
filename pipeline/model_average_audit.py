#!/usr/bin/env python3
"""Exploratory two-model average of LCDM and CPL fate compatibility."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "runs/phase3/fparam/model_average_audit.json"


def compute(prior_odds_cpl_over_lcdm: float = 1.0) -> dict:
    evidence = json.loads((ROOT / "runs/phase2/nested_d0.json").read_text())
    fate = json.loads((ROOT / "runs/phase2/fate/d0_cpl_p1.json").read_text())
    posterior_odds = prior_odds_cpl_over_lcdm * np.exp(evidence["lnB_CPL_over_LCDM"])
    p_cpl = float(posterior_odds / (1.0 + posterior_odds))
    p_lcdm = 1.0 - p_cpl
    p_heat = p_lcdm + p_cpl * fate["P_heat_death_compatible"]
    return {
        "status": "exploratory post-hoc diagnostic",
        "models": ["LCDM", "CPL"],
        "prior_odds_CPL_over_LCDM": prior_odds_cpl_over_lcdm,
        "lnB_CPL_over_LCDM": evidence["lnB_CPL_over_LCDM"],
        "posterior_P_LCDM": p_lcdm,
        "posterior_P_CPL": p_cpl,
        "model_averaged_P_heat_death_compatible": float(p_heat),
        "caution": (
            "depends on the chosen model set and model prior odds; it is not a "
            "preregistered headline result"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prior-odds", type=float, default=1.0)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    result = compute(args.prior_odds)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.output}")
    print(
        f"P(LCDM|D)={result['posterior_P_LCDM']:.4f}, "
        f"P(heat|D)={result['model_averaged_P_heat_death_compatible']:.6f}"
    )


if __name__ == "__main__":
    main()
