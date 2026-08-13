#!/usr/bin/env python3
"""Prepare and run the unblinded WP4 F0 CPL/LCDM posterior maximizations."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cobaya.yaml import yaml_dump, yaml_load_file

from pipeline.audit_wp4_f0_reproduction import (
    FINAL_STOP_AUDIT,
    LOCAL_BESTFIT_ROOT,
    OFFICIAL_BESTFIT_ROOT,
    WP4ReproductionError,
    atomic_write_json,
    display_path,
    parse_one_point,
    sha256_file,
)


BASE_CONFIG = ROOT / "pipeline" / "wp4_f0.yaml"
SOURCE_COVMAT = ROOT / "runs" / "prd_extension" / "wp4_full_cmb" / "f1_proposal.covmat"
PLAN_PATH = LOCAL_BESTFIT_ROOT / "run_plan.json"
COMPLETION_PATH = LOCAL_BESTFIT_ROOT / "completion.json"
COBAYA = ROOT / ".venv" / "bin" / "cobaya-run"
MODEL_SPECS = {
    "cpl": {
        "official": OFFICIAL_BESTFIT_ROOT / "base_w_wa" / "bestfit.minimum.txt",
        "seed": 2026081301,
    },
    "lcdm": {
        "official": OFFICIAL_BESTFIT_ROOT / "base" / "bestfit.minimum.txt",
        "seed": 2026081302,
    },
}


def _read_covmat(path: Path) -> tuple[list[str], np.ndarray]:
    with path.open(encoding="utf-8") as stream:
        line = stream.readline().strip()
    if not line.startswith("#"):
        raise WP4ReproductionError(f"missing covariance header: {path}")
    names = line[1:].split()
    matrix = np.loadtxt(path, comments="#", ndmin=2)
    if matrix.shape != (len(names), len(names)):
        raise WP4ReproductionError(
            f"covariance shape mismatch: {matrix.shape} versus {len(names)}"
        )
    return names, matrix


def write_subcovmat(source: Path, target: Path, excluded: set[str]) -> dict:
    names, matrix = _read_covmat(source)
    keep = [i for i, name in enumerate(names) if name not in excluded]
    kept_names = [names[i] for i in keep]
    selected = matrix[np.ix_(keep, keep)]
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.tmp-{os.getpid()}")
    np.savetxt(temporary, selected, header=" ".join(kept_names))
    os.replace(temporary, target)
    return {
        "path": display_path(target),
        "sha256": sha256_file(target),
        "parameters": kept_names,
        "shape": list(selected.shape),
        "minimum_eigenvalue": float(np.linalg.eigvalsh(selected).min()),
    }


def build_config(model: str, covmat: Path) -> tuple[dict, Path]:
    if model not in MODEL_SPECS:
        raise WP4ReproductionError(f"unknown model: {model}")
    info = yaml_load_file(str(BASE_CONFIG))
    info["packages_path"] = str(ROOT / "data" / "cobaya_packages")
    official = parse_one_point(MODEL_SPECS[model]["official"])
    if model == "lcdm":
        info["params"]["w"] = -1.0
        info["params"]["wa"] = 0.0
    sampled = [
        name
        for name, definition in info["params"].items()
        if isinstance(definition, dict) and "prior" in definition
    ]
    missing = [name for name in sampled if name not in official]
    if missing:
        raise WP4ReproductionError(
            f"official {model} posterior maximum lacks sampled parameters {missing}"
        )
    for name in sampled:
        info["params"][name]["ref"] = float(official[name])
    output = LOCAL_BESTFIT_ROOT / model / "bestfit"
    info["sampler"] = {
        "minimize": {
            "method": "bobyqa",
            "ignore_prior": False,
            "best_of": 1,
            "seed": int(MODEL_SPECS[model]["seed"]),
            "max_evals": 2000,
            "override_bobyqa": {"rhoend": 0.05},
            "covmat": str(covmat),
        }
    }
    info["output"] = str(output)
    config_path = LOCAL_BESTFIT_ROOT / model / "bestfit.yaml"
    return info, config_path


def prepare() -> dict:
    final = json.loads(FINAL_STOP_AUDIT.read_text(encoding="utf-8"))
    if final.get("status") != "EXTERNALLY_STOPPED" or not final.get(
        "post_termination_gates_pass"
    ):
        raise WP4ReproductionError("cannot optimize before successful F0 closure")
    if PLAN_PATH.exists():
        return json.loads(PLAN_PATH.read_text(encoding="utf-8"))

    cpl_covmat = SOURCE_COVMAT
    lcdm_covmat = LOCAL_BESTFIT_ROOT / "lcdm" / "proposal.covmat"
    lcdm_covmat_record = write_subcovmat(
        SOURCE_COVMAT, lcdm_covmat, excluded={"w", "wa"}
    )
    models = {}
    for model, covmat in (("cpl", cpl_covmat), ("lcdm", lcdm_covmat)):
        info, config_path = build_config(model, covmat)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(yaml_dump(info), encoding="utf-8")
        models[model] = {
            "config": str(config_path.relative_to(ROOT)),
            "config_sha256": sha256_file(config_path),
            "output": str((LOCAL_BESTFIT_ROOT / model / "bestfit").relative_to(ROOT)),
            "official_start": str(MODEL_SPECS[model]["official"].relative_to(ROOT)),
            "official_start_sha256": sha256_file(MODEL_SPECS[model]["official"]),
            "seed": MODEL_SPECS[model]["seed"],
            "covmat": str(covmat.relative_to(ROOT)),
            "covmat_sha256": sha256_file(covmat),
        }
    plan = {
        "schema_version": "wp4-f0-bestfit-plan-v1",
        "status": "FROZEN_BEFORE_OPTIMIZATION",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "unblinded F0 reproduction delta-chi2 gate",
        "fate_quantities_computed": False,
        "objective": "maximum posterior separately in CPL and flat LCDM",
        "reported_statistic": (
            "likelihood chi2(CPL MAP) minus likelihood chi2(LCDM MAP)"
        ),
        "optimizer": {
            "implementation": "Cobaya 3.6.2 Py-BOBYQA",
            "method": "bobyqa",
            "ignore_prior": False,
            "best_of": 1,
            "max_evals": 2000,
            "rhoend": 0.05,
            "starting_points": "DESI official posterior maxima",
            "starting_point_role": "optimizer initialization only",
        },
        "parallel_models": 2,
        "environment": {
            "python": str((ROOT / ".venv" / "bin" / "python").resolve()),
            "cobaya_run": str(COBAYA),
            "omp_num_threads": 1,
        },
        "base_config": str(BASE_CONFIG.relative_to(ROOT)),
        "base_config_sha256": sha256_file(BASE_CONFIG),
        "final_stop_audit": str(FINAL_STOP_AUDIT.relative_to(ROOT)),
        "final_stop_audit_sha256": sha256_file(FINAL_STOP_AUDIT),
        "source_covmat": str(SOURCE_COVMAT.relative_to(ROOT)),
        "source_covmat_sha256": sha256_file(SOURCE_COVMAT),
        "lcdm_covmat": lcdm_covmat_record,
        "models": models,
    }
    atomic_write_json(PLAN_PATH, plan)
    return plan


def _run_model(model: str, record: dict) -> dict:
    config = ROOT / record["config"]
    log = config.parent / "bestfit.log"
    env = os.environ.copy()
    env.update(
        {
            "OMP_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "VECLIB_MAXIMUM_THREADS": "1",
            "NUMEXPR_NUM_THREADS": "1",
        }
    )
    started = datetime.now(timezone.utc).isoformat()
    with log.open("w", encoding="utf-8") as stream:
        result = subprocess.run(
            [str(COBAYA), str(config), "--force", "--no-mpi"],
            cwd=ROOT,
            env=env,
            stdout=stream,
            stderr=subprocess.STDOUT,
            check=False,
        )
    minimum = config.parent / "bestfit.minimum.txt"
    return {
        "model": model,
        "started_at_utc": started,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "returncode": int(result.returncode),
        "log": str(log.relative_to(ROOT)),
        "log_sha256": sha256_file(log),
        "minimum_present": minimum.is_file(),
        "minimum": str(minimum.relative_to(ROOT)),
        "minimum_sha256": sha256_file(minimum) if minimum.is_file() else None,
    }


def run(jobs: int = 2) -> dict:
    if jobs != 2:
        raise WP4ReproductionError("the frozen run plan requires two parallel models")
    plan = prepare()
    if COMPLETION_PATH.exists():
        return json.loads(COMPLETION_PATH.read_text(encoding="utf-8"))
    for model, record in plan["models"].items():
        path = ROOT / record["config"]
        if sha256_file(path) != record["config_sha256"]:
            raise WP4ReproductionError(f"frozen optimizer config changed: {path}")
    with ThreadPoolExecutor(max_workers=jobs) as executor:
        futures = {
            model: executor.submit(_run_model, model, record)
            for model, record in plan["models"].items()
        }
        results = {model: future.result() for model, future in futures.items()}
    passed = all(
        record["returncode"] == 0 and record["minimum_present"]
        for record in results.values()
    )
    completion = {
        "schema_version": "wp4-f0-bestfit-completion-v1",
        "status": "PASS" if passed else "FAIL",
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "run_plan": str(PLAN_PATH.relative_to(ROOT)),
        "run_plan_sha256": sha256_file(PLAN_PATH),
        "models": results,
    }
    if passed:
        rows = {
            model: parse_one_point(ROOT / record["minimum"])
            for model, record in results.items()
        }
        completion["likelihood_chi2"] = {
            model: row["chi2"] for model, row in rows.items()
        }
        completion["delta_chi2_cpl_minus_lcdm"] = (
            rows["cpl"]["chi2"] - rows["lcdm"]["chi2"]
        )
    atomic_write_json(COMPLETION_PATH, completion)
    return completion


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--jobs", type=int, default=2)
    args = parser.parse_args()
    result = prepare() if args.prepare_only else run(args.jobs)
    print(json.dumps({
        "status": result["status"],
        "plan": str(PLAN_PATH.relative_to(ROOT)),
        "completion": str(COMPLETION_PATH.relative_to(ROOT)),
    }, sort_keys=True))
    return 0 if result["status"] in {"FROZEN_BEFORE_OPTIMIZATION", "PASS"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
