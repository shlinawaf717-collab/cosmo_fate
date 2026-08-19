#!/usr/bin/env python3
"""Freeze full-likelihood PolyChord configs for WP4 F1 evidence and tail checks."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from cobaya.yaml import yaml_dump, yaml_load_file


REPO_ROOT = Path(__file__).resolve().parents[1]
SEEDS = (2026082001, 2026082002, 2026082003)
MODELS = ("cpl", "rip", "decay", "lcdm")
NLIVE = 500
NUM_REPEATS = "5d"
PRECISION = 0.01
P1_AREAS = {"full_box": 20.0, "p1": 15.5, "rip_box": 8.0,
            "rip_p1": 4.0, "decay_box": 12.0, "decay_p1": 11.5}


class F1NestedPreparationError(RuntimeError):
    """Raised when a nested run would differ from its prospectively frozen plan."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(payload, handle, indent=2, sort_keys=True); handle.write("\n")
        handle.flush(); os.fsync(handle.fileno()); temporary = Path(handle.name)
    os.replace(temporary, path)


def corrections() -> dict:
    return {
        "cpl": math.log(P1_AREAS["full_box"] / P1_AREAS["p1"]),
        "rip": math.log(P1_AREAS["rip_box"] / P1_AREAS["rip_p1"]),
        "decay": math.log(P1_AREAS["decay_box"] / P1_AREAS["decay_p1"]),
        "lcdm": 0.0,
    }


def build_config(base: dict, model: str, seed: int, project_root: Path,
                 packages_path: Path, polychord_path: Path, output_root: Path) -> dict:
    if model not in MODELS or seed not in SEEDS:
        raise F1NestedPreparationError("unknown nested model or seed")
    info = copy.deepcopy(base)
    info["packages_path"] = str(packages_path.resolve())
    info["theory"]["camb"]["path"] = "global"
    if model == "lcdm":
        info["params"]["w"] = -1.0; info["params"]["wa"] = 0.0
        info.pop("prior", None)
    elif model == "rip":
        info["params"]["wa"]["prior"] = {"min": 0.0, "max": 2.0}
        info["params"]["wa"]["ref"] = {"dist": "norm", "loc": 0.1, "scale": 0.03}
    elif model == "decay":
        info["params"]["wa"]["prior"] = {"min": -3.0, "max": 0.0}
    blocking = copy.deepcopy(base["sampler"]["mcmc"]["blocking"])
    if model == "lcdm":
        for block in blocking:
            block[1] = [name for name in block[1] if name not in {"w", "wa"}]
        blocking = [block for block in blocking if block[1]]
    info["sampler"] = {"polychord": {
        "path": str(polychord_path.resolve()), "nlive": NLIVE,
        "num_repeats": NUM_REPEATS, "nprior": "10nlive", "nfail": "nlive",
        "do_clustering": True, "precision_criterion": PRECISION,
        "max_ndead": float("inf"), "boost_posterior": 0, "posteriors": True,
        "equals": True, "cluster_posteriors": True, "write_resume": True,
        "read_resume": True, "write_stats": True, "write_live": True,
        "write_dead": True, "write_prior": True, "synchronous": False,
        "measure_speeds": False, "blocking": blocking,
        "confidence_for_unbounded": 0.9999995, "seed": seed,
    }}
    info["output"] = str((output_root / f"seed{seed}/{model}/chain").resolve())
    return info


def prepare(project_root: Path, base_config: Path, packages_path: Path,
            polychord_path: Path, output_root: Path, platform_role: str) -> dict:
    plan_path = output_root / "run_plan.json"
    activation_path = output_root / "activation.json"
    existing_products = list(output_root.glob("seed*/*/chain.*.txt")) + list(
        output_root.glob("seed*/*/chain.evidence.yaml"))
    if existing_products and not plan_path.exists():
        raise F1NestedPreparationError("nested products exist without a frozen plan")
    if plan_path.exists():
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        for record in plan["runs"]:
            path = project_root / record["config"] if not Path(record["config"]).is_absolute() else Path(record["config"])
            if sha256_file(path) != record["config_sha256"]:
                raise F1NestedPreparationError(f"frozen config changed: {path}")
        return plan
    base = yaml_load_file(str(base_config))
    output_root.mkdir(parents=True, exist_ok=True)
    runs = []
    for seed in SEEDS:
        for model in MODELS:
            path = output_root / f"configs/seed{seed}_{model}.yaml"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(yaml_dump(build_config(base, model, seed, project_root,
                                                   packages_path, polychord_path, output_root)),
                            encoding="utf-8")
            runs.append({
                "seed": seed, "model": model, "config": str(path.relative_to(project_root)),
                "config_sha256": sha256_file(path),
                "output": str((output_root / f"seed{seed}/{model}/chain").relative_to(project_root)),
                "conditional_logZ_correction": corrections()[model],
            })
    if platform_role not in {"template", "wsl2_production"}:
        raise F1NestedPreparationError(f"unknown platform role: {platform_role}")
    plan = {
        "schema_version": "wp4-f1-polychord-plan-v1",
        "status": ("FROZEN_BEFORE_NESTED_PRODUCTION" if platform_role == "wsl2_production"
                   else "FROZEN_TEMPLATE_NO_PRODUCTION_AUTHORITY"),
        "platform_role": platform_role,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "engine": {"cobaya": "3.6.2", "polychordlite": "1.20.1", "nlive": NLIVE,
                   "num_repeats": NUM_REPEATS, "precision_criterion": PRECISION,
                   "mpi_ranks_per_run": 4, "parallel_runs": 2, "threads_per_rank": 1},
        "seeds": list(SEEDS), "models": list(MODELS), "runs": runs,
        "p1_geometry": {**P1_AREAS, "conditional_logZ_corrections": corrections(),
                        "rip_fraction_within_p1": P1_AREAS["rip_p1"] / P1_AREAS["p1"],
                        "decay_fraction_within_p1": P1_AREAS["decay_p1"] / P1_AREAS["p1"]},
        "base_config": str(base_config.relative_to(project_root)),
        "base_config_sha256": sha256_file(base_config),
        "pre_result_scope": "MCMC and best-fit endpoints known; no nested output inspected or created.",
    }
    atomic_json(plan_path, plan)
    if platform_role == "wsl2_production":
        runtime_files = {
            "preparation": Path(__file__).resolve(),
            "driver": Path(__file__).with_name("run_wp4_f1_nested.py").resolve(),
            "reporter": Path(__file__).with_name("report_wp4_f1_nested.py").resolve(),
            "fate_classifier": Path(__file__).with_name("fate.py").resolve(),
        }
        missing = [name for name, path in runtime_files.items() if not path.is_file()]
        if missing:
            raise F1NestedPreparationError(f"nested runtime files are missing: {missing}")
        activation = {
            "schema_version": "wp4-f1-polychord-activation-v1",
            "status": "ACTIVE_BEFORE_NESTED_PRODUCTION",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "plan_sha256": sha256_file(plan_path),
            "preparation_code_sha256": sha256_file(Path(__file__).resolve()),
            "configs": {f"{row['seed']}_{row['model']}": row["config_sha256"] for row in runs},
            "runtime_hashes": {
                name: {"path": str(path.relative_to(project_root)), "sha256": sha256_file(path)}
                for name, path in runtime_files.items()
            },
            "nested_samples_exist": False,
        }
        atomic_json(activation_path, activation)
    return plan


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--base-config", type=Path)
    parser.add_argument("--packages-path", type=Path)
    parser.add_argument("--polychord-path", type=Path)
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--platform-role", choices=("template", "wsl2_production"), default="template")
    args = parser.parse_args()
    project = args.project_root.resolve()
    base = (args.base_config or project / "pipeline/wp4_f1.yaml").resolve()
    packages = (args.packages_path or project / "data/cobaya_packages").resolve()
    polychord = (args.polychord_path or project / "work/nested_packages/code/PolyChordLite").resolve()
    output = (args.output_root or project / "runs/prd_extension/wp4_full_cmb/f1_nested").resolve()
    plan = prepare(project, base, packages, polychord, output, args.platform_role)
    print(json.dumps({"status": plan["status"], "runs": len(plan["runs"]), "output": str(output)}))
    return 0


if __name__ == "__main__": raise SystemExit(main())
