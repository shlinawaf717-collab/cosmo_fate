#!/usr/bin/env python3
"""Audit the WP6 no-sampling initialization artifacts."""

import json
from datetime import datetime, timezone
from pathlib import Path

from cobaya.yaml import yaml_load_file

from pipeline.audit_wp4_f0_reproduction import atomic_write_json, sha256_file


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "runs/prd_extension/wp6_growth"
SMOKE = RUN / "smoke"
OUT = RUN / "smoke_audit.json"


def audit() -> dict:
    plan = json.loads((RUN / "config_plan.json").read_text())
    config = ROOT / plan["config"]
    if sha256_file(config) != plan["config_sha256"]:
        raise RuntimeError("WP6 frozen configuration hash mismatch")

    updated = yaml_load_file(str(SMOKE / "chain.updated.yaml"))
    like = updated["likelihood"]
    theory = updated["theory"]
    sample_files = sorted(SMOKE.glob("chain.*.txt"))
    required = [
        SMOKE / "chain.input.yaml",
        SMOKE / "chain.updated.yaml",
        SMOKE / "chain.checkpoint",
        SMOKE / "chain.progress",
        SMOKE / "chain.covmat",
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
    checks = {
        "required_initialization_artifacts_present": not missing,
        "dr2_bao_absent": "bao.desi_dr2.desi_bao_all" not in like,
        "dr1_fs_bao_present": "pipeline.wp6_desi_fs.DESIDR1FSBAO" in like,
        "dr1_theory_present": (
            "pipeline.wp6_desi_fs.DESIDR1ReptVelocileptors" in theory
        ),
        "posterior_sample_rows_zero": not sample_files,
        "fate_calculation_not_performed": True,
    }
    result = {
        "schema_version": "wp6-no-sampling-smoke-audit-v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "missing": missing,
        "likelihood_evaluated_during_initialization": True,
        "scientific_endpoint_generated": False,
        "artifacts": {
            str(path.relative_to(ROOT)): {
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
            for path in required
            if path.is_file()
        },
        "config_sha256": plan["config_sha256"],
    }
    atomic_write_json(OUT, result)
    if result["status"] != "PASS":
        raise RuntimeError(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    print(json.dumps(audit(), indent=2))
