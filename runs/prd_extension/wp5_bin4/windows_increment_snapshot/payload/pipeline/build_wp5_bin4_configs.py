#!/usr/bin/env python3
"""Build and freeze the three registered full-likelihood WP5 BIN4 configs."""

from __future__ import annotations

import argparse
import copy
import json
from datetime import datetime, timezone
from pathlib import Path

from cobaya.yaml import yaml_dump, yaml_load_file

from pipeline.audit_wp4_f0_reproduction import atomic_write_json, sha256_file
from pipeline.wp5_bin4 import SENSITIVITY_DELTAS


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "pipeline/wp4_f1.yaml"
FORMAL_GATE = ROOT / "runs/prd_extension/wp5_bin4/formal_theory_gate.json"
AMENDMENT = ROOT / "plan/wp5_smooth_background_amendment_a013.json"
OUTPUT_ROOT = ROOT / "runs/prd_extension/wp5_bin4/configs"
PLAN = ROOT / "runs/prd_extension/wp5_bin4/config_plan.json"
SEEDS = {0.005: 2026082501, 0.01: 2026082502, 0.02: 2026082503}


class WP5ConfigError(RuntimeError):
    """Raised when a WP5 config would violate the amended frozen design."""


def build_config(delta_lna: float) -> dict:
    if delta_lna not in SENSITIVITY_DELTAS:
        raise WP5ConfigError(f"unregistered delta_lna: {delta_lna}")
    info = yaml_load_file(str(BASE))
    camb_info = info["theory"].pop("camb")
    info["theory"]["pipeline.wp5_camb.BIN4CAMB"] = {
        **camb_info,
        "python_path": ".",
        "delta_lna": float(delta_lna),
        "table_base_points": 1200,
        "table_points_per_transition": 240,
    }
    likelihood = {}
    for name, settings in info["likelihood"].items():
        likelihood[name] = settings
    likelihood["pipeline.early_de_gate.Bin4EarlyDEGate"] = {
        "python_path": ".", "z_check": 1059.0, "max_ratio": 0.01,
    }
    info["likelihood"] = likelihood
    params = {}
    for name, definition in info["params"].items():
        if name == "w":
            for ordinal, ref in enumerate((-1.0, -0.9, -1.5, -1.7), 1):
                params[f"w{ordinal}"] = {
                    "prior": {"min": -3.0, "max": 1.0},
                    "ref": {"dist": "norm", "loc": ref, "scale": 0.04},
                    "proposal": 0.05,
                    "latex": f"w_{{{ordinal}}}",
                }
        elif name == "wa":
            continue
        else:
            params[name] = definition
    info["params"] = params
    info["prior"] = {"matter_dom_bin4": "lambda w4: 0 if w4 < 0 else -1e30"}
    mcmc = info["sampler"]["mcmc"]
    mcmc["covmat"] = None
    mcmc["seed"] = SEEDS[delta_lna]
    for block in mcmc["blocking"]:
        if "w" in block[1]:
            index = block[1].index("w")
            block[1][index:index + 2] = ["w1", "w2", "w3", "w4"]
    tag = str(delta_lna).replace(".", "p")
    info["output"] = str(
        ROOT / f"runs/prd_extension/wp5_bin4/production/delta_{tag}/chain"
    )
    return info


def prepare() -> dict:
    gate = json.loads(FORMAL_GATE.read_text(encoding="utf-8"))
    amendment = json.loads(AMENDMENT.read_text(encoding="utf-8"))
    if gate.get("status") != "PASS":
        raise WP5ConfigError("formal WP5 theory gate has not passed")
    if amendment.get("status") != "approved_before_WP5_real_data_inference":
        raise WP5ConfigError("PRD-A013 is not active")
    existing_samples = list(
        (ROOT / "runs/prd_extension/wp5_bin4/production").glob("**/chain.*.txt")
    )
    if existing_samples:
        raise WP5ConfigError("refusing to rebuild configs after WP5 production samples exist")
    if PLAN.exists():
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        for record in plan["configs"]:
            if sha256_file(ROOT / record["path"]) != record["sha256"]:
                raise WP5ConfigError("frozen WP5 config changed")
        return plan
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    records = []
    for delta in SENSITIVITY_DELTAS:
        tag = str(delta).replace(".", "p")
        path = OUTPUT_ROOT / f"wp5_bin4_delta_{tag}.yaml"
        path.write_text(yaml_dump(build_config(delta)), encoding="utf-8")
        records.append({"delta_lna": delta, "seed": SEEDS[delta],
                        "path": str(path.relative_to(ROOT)), "sha256": sha256_file(path)})
    plan = {
        "schema_version": "wp5-bin4-config-plan-v1",
        "status": "FROZEN_BEFORE_FULL_LIKELIHOOD_INITIALIZATION",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "base": str(BASE.relative_to(ROOT)), "base_sha256": sha256_file(BASE),
        "formal_theory_gate": str(FORMAL_GATE.relative_to(ROOT)),
        "formal_theory_gate_sha256": sha256_file(FORMAL_GATE),
        "amendment": str(AMENDMENT.relative_to(ROOT)),
        "amendment_sha256": sha256_file(AMENDMENT),
        "configs": records,
        "unchanged_primary_delta_lna": 0.01,
        "optional_width_selection": False,
        "real_data_likelihood_evaluated": False,
        "posterior_or_fate_result_generated": False,
    }
    atomic_write_json(PLAN, plan)
    return plan


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--print-config", type=float)
    args = parser.parse_args()
    if args.print_config is not None:
        print(yaml_dump(build_config(args.print_config))); return 0
    plan = prepare(); print(json.dumps({"status": plan["status"], "configs": len(plan["configs"])}))
    return 0


if __name__ == "__main__": raise SystemExit(main())
