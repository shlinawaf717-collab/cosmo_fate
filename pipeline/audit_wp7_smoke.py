#!/usr/bin/env python3
"""Audit five endpoint-blind WP7 D0 no-sampling smoke initializations."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from cobaya.yaml import yaml_load_file

from pipeline.audit_wp4_f0_reproduction import sha256_file
from pipeline.build_wp7_configs import PLAN, ROOT, SETTINGS


OUTPUT = ROOT / "runs/prd_extension/wp7/smoke_audit.json"


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as stream:
        json.dump(payload, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
        temporary = Path(stream.name)
    os.replace(temporary, path)


def audit() -> dict:
    created_at = (
        json.loads(OUTPUT.read_text())["created_at_utc"]
        if OUTPUT.is_file()
        else datetime.now(timezone.utc).isoformat()
    )
    plan = json.loads(PLAN.read_text())
    records = []
    for tag in SETTINGS:
        record = plan["configs"][tag]
        config = ROOT / record["path"]
        run = ROOT / f"runs/prd_extension/wp7/development/{tag}"
        updated = run / "chain.updated.yaml"
        input_yaml = run / "chain.input.yaml"
        samples = list(run.glob("chain.*.txt"))
        parsed = yaml_load_file(str(updated)) if updated.is_file() else {}
        checks = {
            "config_hash": sha256_file(config) == record["sha256"],
            "input_yaml_present": input_yaml.is_file(),
            "updated_yaml_present": updated.is_file(),
            "fs7_background_loaded": "pipeline.bgtheory.BackgroundW" in parsed.get("theory", {}),
            "d0_components_present": all(name in parsed.get("likelihood", {}) for name in (
                "bao.desi_dr2.desi_bao_all",
                "sn.pantheonplusshoes",
                "pipeline.cmb_distprior.ProviderDistPrior",
            )),
            "posterior_sample_rows_zero": not samples,
        }
        records.append({"tag": tag, "checks": checks, "pass": all(checks.values())})
    payload = {
        "schema_version": "wp7-fs7-no-sampling-smoke-v1",
        "created_at_utc": created_at,
        "status": "PASS" if all(row["pass"] for row in records) else "FAIL",
        "settings": records,
        "likelihood_evaluated_during_initialization": True,
        "posterior_sampling_performed": False,
        "fate_endpoint_calculated": False,
        "production_authorized": False,
    }
    atomic_json(OUTPUT, payload)
    return payload


if __name__ == "__main__":
    print(json.dumps(audit(), indent=2, sort_keys=True))
