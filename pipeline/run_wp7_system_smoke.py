#!/usr/bin/env python3
"""Run five no-sampling smokes against the frozen WP7 production configs."""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone

from cobaya.yaml import yaml_dump, yaml_load_file

from pipeline.audit_wp4_f0_reproduction import atomic_write_json
from pipeline.freeze_wp7_system import PLAN, ROOT, SMOKE, SYSTEM


def run() -> dict:
    plan = json.loads(PLAN.read_text())
    records = []
    for tag in plan["settings"]:
        source = ROOT / next(row["config"] for row in plan["chains"] if row["setting"] == tag and row["chain"] == 1)
        info = yaml_load_file(str(source))
        directory = SYSTEM / "smoke" / tag; directory.mkdir(parents=True, exist_ok=True)
        info["output"] = str(directory / "chain")
        config = directory / "smoke.yaml"; config.write_text(yaml_dump(info))
        env = os.environ.copy(); env["PYTHONPATH"] = str(ROOT)
        env.update({name: "1" for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")})
        completed = subprocess.run([str(ROOT / ".venv/bin/cobaya-run"), "--test", str(config)], cwd=ROOT, env=env, capture_output=True, text=True)
        log = completed.stdout + "\n" + completed.stderr
        (directory / "smoke.log").write_text(log)
        samples = list(directory.glob("chain.*.txt"))
        passed = completed.returncode == 0 and "Test initialization successful" in log and not samples
        records.append({"setting": tag, "returncode": completed.returncode, "pass": passed, "sample_files": [str(path) for path in samples]})
    payload = {
        "schema_version": "wp7-fs7-production-system-smoke-v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if all(row["pass"] for row in records) else "FAIL",
        "settings": records,
        "sampling_performed": False, "posterior_generated": False, "fate_calculation_performed": False,
    }
    atomic_write_json(SMOKE, payload); return payload


if __name__ == "__main__":
    result = run(); print(json.dumps({"status": result["status"], "settings": len(result["settings"])})); raise SystemExit(0 if result["status"] == "PASS" else 1)
