#!/usr/bin/env python3
"""Deterministic interface audit for a full-Planck BIN4 likelihood run."""

from __future__ import annotations

import json
from pathlib import Path

try:
    from pipeline.bgtheory import BackgroundW
except ModuleNotFoundError:  # pragma: no cover
    from bgtheory import BackgroundW

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "runs/phase3/fparam/full_planck_feasibility.json"


def compute() -> dict:
    provided = list(BackgroundW.get_can_provide(None))
    required = ["Cl"]
    missing = [name for name in required if name not in provided]
    return {
        "schema_version": "full-planck-feasibility-v1",
        "target": "BIN4 with Planck 2018 full TT/TE/EE+lowE likelihood",
        "theory_interface": "pipeline.bgtheory.BackgroundW",
        "provided_products": provided,
        "required_spectrum_products": required,
        "missing_products": missing,
        "has_perturbation_evolution": False,
        "decision": "NO-GO" if missing else "GO",
        "run_performed": False,
        "reason": (
            "BackgroundW is a geometry-only background solver and cannot predict the CMB "
            "angular spectra required by the full Planck likelihood. A valid run requires "
            "a Boltzmann perturbation implementation for the BIN4 history and installed "
            "Planck likelihood data; substituting distance priors is not a full-Planck run."
        ),
        "current_scope": "BIN4 results remain compressed-CMB-conditioned and are downgraded accordingly",
        "restart_conditions": [
            "implement and validate BIN4 perturbations in a Boltzmann solver",
            "install the official Planck likelihood and nuisance-data package",
            "revalidate CPL against the existing full-likelihood benchmark before BIN4 inference",
        ],
    }


if __name__ == "__main__":
    out = compute()
    OUT.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT}: {out['decision']}")
