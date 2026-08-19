#!/usr/bin/env python3
"""Create the final hash-bound authorization immediately before WP7 starts."""

import argparse
import hashlib
import json
from datetime import datetime, timezone

from pipeline.audit_wp4_f0_reproduction import atomic_write_json
from pipeline.evaluate_wp7_stop import ACTIVATION, SYSTEM, validate


def authorize(kind: str = "real") -> dict:
    if kind == "real":
        validate(); output = SYSTEM / "WP7_PRODUCTION_STARTED.json"
        plan = SYSTEM / "run_plan.json"; activation = ACTIVATION
    else:
        from pipeline.freeze_wp7_sbc_system import ACTIVATION as activation, PLAN, freeze
        freeze(); plan = PLAN; output = PLAN.parent / "WP7_SBC_STARTED.json"
    if output.is_file():
        return json.loads(output.read_text())
    payload = {
        "schema_version": f"wp7-fs7-{kind}-start-v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "production_authorized": True,
        ("run_plan_sha256" if kind == "real" else "plan_sha256"): hashlib.sha256(plan.read_bytes()).hexdigest(),
        "activation_sha256": hashlib.sha256(activation.read_bytes()).hexdigest(),
        "scientific_endpoints_inspected_before_start": False,
    }
    atomic_write_json(output, payload)
    return payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("kind", choices=("real", "sbc")); args = parser.parse_args()
    print(json.dumps(authorize(args.kind), indent=2, sort_keys=True))
