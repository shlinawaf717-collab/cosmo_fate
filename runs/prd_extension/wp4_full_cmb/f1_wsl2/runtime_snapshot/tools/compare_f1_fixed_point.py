#!/usr/bin/env python3
"""Compare Mac and WSL2 F1 fixed-point likelihood fingerprints."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


TOTAL_CHI2_ABSOLUTE_MAX = 0.10
COMPONENT_CHI2_ABSOLUTE_MAX = 0.10


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    reference = json.loads(args.reference.read_text(encoding="utf-8"))
    candidate = json.loads(args.candidate.read_text(encoding="utf-8"))
    if reference["fixed_point"] != candidate["fixed_point"]:
        raise ValueError("fixed points differ")
    if set(reference["component_chi2"]) != set(candidate["component_chi2"]):
        raise ValueError("likelihood component names differ")
    components = {}
    for name in sorted(reference["component_chi2"]):
        difference = candidate["component_chi2"][name] - reference["component_chi2"][name]
        components[name] = {
            "signed_difference": difference,
            "absolute_difference": abs(difference),
            "pass": abs(difference) <= COMPONENT_CHI2_ABSOLUTE_MAX,
        }
    total_difference = candidate["total_likelihood_chi2"] - reference["total_likelihood_chi2"]
    gates = {
        "total_chi2": abs(total_difference) <= TOTAL_CHI2_ABSOLUTE_MAX,
        "all_component_chi2": all(item["pass"] for item in components.values()),
    }
    payload = {
        "schema_version": "wp4-f1-cross-platform-fixed-point-comparison-v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if all(gates.values()) else "FAIL",
        "thresholds_frozen_before_wsl2_result": {
            "total_chi2_absolute_maximum": TOTAL_CHI2_ABSOLUTE_MAX,
            "component_chi2_absolute_maximum": COMPONENT_CHI2_ABSOLUTE_MAX,
        },
        "gates": gates,
        "total_chi2": {
            "reference": reference["total_likelihood_chi2"],
            "candidate": candidate["total_likelihood_chi2"],
            "signed_difference": total_difference,
            "absolute_difference": abs(total_difference),
        },
        "components": components,
        "scope_warning": "Passing is a pre-production drift screen, not posterior equivalence.",
    }
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "output": str(args.output)}))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
