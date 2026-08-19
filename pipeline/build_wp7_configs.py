#!/usr/bin/env python3
"""Build endpoint-blind D0 development configs for the five frozen FS7 priors."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from cobaya.yaml import yaml_dump, yaml_load_file

from pipeline.wp7_fs7 import cholesky


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "pipeline/fparam_base.yaml"
PROTOCOL = ROOT / "plan/prd_extension_protocol.json"
OUTPUT = ROOT / "runs/prd_extension/wp7/configs"
PLAN = ROOT / "runs/prd_extension/wp7/config_plan.json"
SETTINGS = {
    "primary": (0.5, 0.7, "admissibility_primary"),
    "sig025": (0.25, 0.7, "admissibility_sig025"),
    "sig100": (1.0, 0.7, "admissibility_sig100"),
    "ell035": (0.5, 0.35, "admissibility_ell035"),
    "ell140": (0.5, 1.4, "admissibility_ell140"),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as stream:
        json.dump(payload, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
        temporary = Path(stream.name)
    os.replace(temporary, path)


def _node_lambda(row) -> str:
    arguments = ",".join(f"z{i}" for i in range(1, 8))
    terms = " + ".join(f"({coefficient:.17g})*z{i}" for i, coefficient in enumerate(row, 1))
    return f"lambda {arguments}: -1.0 + {terms}"


def build(tag: str) -> dict:
    sigma_f, ell, prior_function = SETTINGS[tag]
    info = copy.deepcopy(yaml_load_file(str(BASE)))
    info["theory"]["pipeline.bgtheory.BackgroundW"]["model"] = "fs7"
    info["prior"] = {
        "fs7_function_bounds": f"import_module('pipeline.wp7_fs7').{prior_function}"
    }
    info["params"].pop("w")
    info["params"].pop("wa")
    for index in range(1, 8):
        info["params"][f"z{index}"] = {
            "prior": {"dist": "norm", "loc": 0.0, "scale": 1.0},
            "ref": {"dist": "norm", "loc": 0.0, "scale": 0.15},
            "proposal": 0.15,
            "drop": True,
            "latex": f"z_{{{index}}}",
        }
    factor = cholesky(sigma_f, ell)
    for index, row in enumerate(factor, 1):
        info["params"][f"fs7_w{index}"] = {
            "value": _node_lambda(row),
            "latex": f"w_{{{index}}}",
        }
    info["sampler"]["mcmc"]["seed"] = 2026083000 + list(SETTINGS).index(tag) + 1
    info["output"] = str(ROOT / f"runs/prd_extension/wp7/development/{tag}/chain")
    info["wp7_metadata"] = {
        "role": "development configuration before WP7 posterior production",
        "sigma_f": sigma_f,
        "ell": ell,
        "truncated_prior": "normalized by conditioning N(0,I) on the registered node and spline bounds",
        "external_prior_normalization": "constant within setting; evidence forbidden until independently estimated",
    }
    return info


def prepare() -> dict:
    if PLAN.is_file():
        plan = json.loads(PLAN.read_text())
        for record in plan["configs"].values():
            if sha256(ROOT / record["path"]) != record["sha256"]:
                raise RuntimeError("frozen WP7 development config hash mismatch")
        return plan
    OUTPUT.mkdir(parents=True, exist_ok=True)
    configs = {}
    for tag in SETTINGS:
        path = OUTPUT / f"fs7_{tag}.yaml"
        path.write_text(yaml_dump(build(tag)), encoding="utf-8")
        configs[tag] = {"path": str(path.relative_to(ROOT)), "sha256": sha256(path)}
    plan = {
        "schema_version": "wp7-fs7-development-config-plan-v1",
        "status": "FROZEN_BEFORE_D0_NO_SAMPLING_SMOKE",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "base_config": {"path": str(BASE.relative_to(ROOT)), "sha256": sha256(BASE)},
        "protocol": {"path": str(PROTOCOL.relative_to(ROOT)), "sha256": sha256(PROTOCOL)},
        "configs": configs,
        "posterior_production_authorized": False,
        "fate_calculation_authorized": False,
        "evidence_authorized": False,
    }
    atomic_json(PLAN, plan)
    return plan


if __name__ == "__main__":
    print(json.dumps(prepare(), indent=2, sort_keys=True))
