#!/usr/bin/env python3
"""Run and audit no-sampling full-likelihood smoke tests for all WP5 widths."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from pipeline.audit_wp4_f0_reproduction import atomic_write_json, sha256_file
from pipeline.build_wp5_bin4_configs import PLAN, ROOT, prepare


DEFAULT_OUTPUT = ROOT / "runs/prd_extension/wp5_bin4/smoke_audit.json"
COBAYA = ROOT / ".venv/bin/cobaya-run"


def environment() -> dict:
    env = os.environ.copy()
    env.update({name: "1" for name in (
        "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")})
    env["PYTHONPATH"] = str(ROOT)
    return env


def audit_log(text: str) -> dict:
    return {
        "test_initialization_success": "Test initialization successful" in text,
        "dynamic_BIN4CAMB_loaded": "pipeline.wp5_camb.bin4camb" in text.lower(),
        "desi_initialized": "[bao.desi_dr2.desi_bao_all] Initialized." in text,
        "two_clik_self_checks": text.count("Checking likelihood") == 2,
        "npipe_initialized": "Number of data points: 9915" in text,
        "act_initialized": "Loading ACT DR6 lensing likelihood v1.2" in text,
        "four_bin_initial_point": all(f"w{i}:" in text for i in range(1, 5)),
        "registered_seed": "This run has been SEEDED" in text,
    }


def run(output: Path) -> dict:
    plan = prepare(); records = []
    for record in plan["configs"]:
        config = ROOT / record["path"]
        if sha256_file(config) != record["sha256"]:
            raise RuntimeError(f"frozen WP5 config changed: {config}")
        log = config.with_suffix(".smoke.log")
        result = subprocess.run(
            [str(COBAYA), str(config), "--test", "--no-mpi", "--force"],
            cwd=ROOT, env=environment(), text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
        )
        log.write_text(result.stdout, encoding="utf-8")
        markers = audit_log(result.stdout)
        tag = str(record["delta_lna"]).replace(".", "p")
        chain_files = list(
            (ROOT / f"runs/prd_extension/wp5_bin4/production/delta_{tag}").glob("chain.*.txt")
        )
        records.append({
            "delta_lna": record["delta_lna"], "seed": record["seed"],
            "config": record["path"], "config_sha256": record["sha256"],
            "returncode": result.returncode, "markers": markers,
            "log": str(log.relative_to(ROOT)), "log_sha256": sha256_file(log),
            "sample_chain_files": [str(path.relative_to(ROOT)) for path in chain_files],
            "pass": result.returncode == 0 and all(markers.values()) and not chain_files,
        })
    payload = {
        "schema_version": "wp5-bin4-full-likelihood-smoke-v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if all(row["pass"] for row in records) else "FAIL",
        "config_plan": str(PLAN.relative_to(ROOT)),
        "config_plan_sha256": sha256_file(PLAN),
        "runs": records,
        "scope": {
            "single_initial_point_likelihood_evaluated_per_width": True,
            "sampling_performed": False,
            "posterior_generated": False,
            "fate_calculation_performed": False,
            "aggregate_scientific_endpoint_generated": False,
        },
    }
    atomic_write_json(output, payload); return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(); payload = run(args.output)
    print(json.dumps({"status": payload["status"], "widths": len(payload["runs"])}))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__": raise SystemExit(main())
