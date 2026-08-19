#!/usr/bin/env python3
"""Prepare and run the frozen WP4 F1 CPL/LCDM posterior maximizations."""

from __future__ import annotations

import argparse
import copy
import json
import math
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from cobaya.yaml import yaml_dump, yaml_load_file

from pipeline.audit_wp4_f0_reproduction import atomic_write_json, parse_one_point, sha256_file


ROOT = Path(__file__).resolve().parents[1]
BASE_CONFIG = ROOT / "pipeline/wp4_f1.yaml"
F1_ROOT = ROOT / "runs/prd_extension/wp4_full_cmb/f1_wsl2"
ENDPOINTS = F1_ROOT / "mcmc_endpoints.json"
BESTFIT_ROOT = ROOT / "runs/prd_extension/wp4_full_cmb/f1_bestfits"
PLAN = BESTFIT_ROOT / "run_plan.json"
SMOKE = BESTFIT_ROOT / "smoke.json"
COMPLETION = BESTFIT_ROOT / "completion.json"
COBAYA = ROOT / ".venv/bin/cobaya-run"
SEEDS = {"cpl": 2026081901, "lcdm": 2026081902}
NOMINAL_DATA_COUNT = 11712


class F1BestfitError(RuntimeError):
    """Raised when an F1 model-comparison optimization is not reproducible."""


def _sampled(info: dict) -> list[str]:
    return [name for name, definition in info["params"].items()
            if isinstance(definition, dict) and "prior" in definition]


def _load_postburn() -> tuple[list[str], np.ndarray, np.ndarray]:
    arrays = []; weights = []; header = None
    for ordinal in range(1, 5):
        path = F1_ROOT / f"raw/work/f1/c{ordinal}/chain.1.txt"
        with path.open(encoding="utf-8") as stream:
            columns = stream.readline().lstrip("#").split()
        if header is None: header = columns
        if columns != header: raise F1BestfitError("F1 chain headers differ")
        data = np.loadtxt(path, comments="#", ndmin=2)
        post = data[int(0.5 * len(data)):]
        arrays.append(post); weights.append(post[:, columns.index("weight")])
    return header, np.concatenate(arrays), np.concatenate(weights)


def write_covmat(path: Path, names: list[str], matrix: np.ndarray) -> dict:
    matrix = np.asarray(matrix, dtype=float)
    if matrix.shape != (len(names), len(names)):
        raise F1BestfitError("covariance shape mismatch")
    eigenvalue = float(np.linalg.eigvalsh(matrix).min())
    if not np.isfinite(eigenvalue) or eigenvalue <= 0:
        raise F1BestfitError(f"covariance is not positive definite: {eigenvalue}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    np.savetxt(temporary, matrix, header=" ".join(names))
    os.replace(temporary, path)
    try:
        display = str(path.relative_to(ROOT))
    except ValueError:
        display = str(path)
    return {"path": display, "sha256": sha256_file(path),
            "parameters": names, "shape": list(matrix.shape), "minimum_eigenvalue": eigenvalue}


def _starts_and_covariance(info: dict) -> tuple[dict, dict, np.ndarray, list[str]]:
    columns, data, weights = _load_postburn()
    names = _sampled(info)
    indices = [columns.index(name) for name in names]
    integer = np.rint(weights).astype(np.int64)
    covariance = np.cov(data[:, indices].T, ddof=0, fweights=integer)
    best = data[np.argmin(data[:, columns.index("minuslogpost")])]
    cpl = {name: float(best[columns.index(name)]) for name in names}
    lcdm = {name: float(np.average(data[:, columns.index(name)], weights=weights))
            for name in names if name not in {"w", "wa"}}
    return cpl, lcdm, covariance, names


def _build_config(model: str, start: dict, covmat: Path) -> dict:
    info = yaml_load_file(str(BASE_CONFIG))
    info["packages_path"] = str(ROOT / "data/cobaya_packages")
    if model == "lcdm":
        info["params"]["w"] = -1.0; info["params"]["wa"] = 0.0
        info.pop("prior", None)
    for name in _sampled(info):
        info["params"][name]["ref"] = float(start[name])
    info["sampler"] = {"minimize": {
        "method": "bobyqa", "ignore_prior": False, "best_of": 1,
        "seed": SEEDS[model], "max_evals": 2000,
        "override_bobyqa": {"rhoend": 0.05}, "covmat": str(covmat),
    }}
    info["output"] = str(BESTFIT_ROOT / model / "bestfit")
    return info


def prepare() -> dict:
    endpoints = json.loads(ENDPOINTS.read_text(encoding="utf-8"))
    if endpoints.get("status") != "PASS_MCMC_NESTED_VERIFICATION_REQUIRED":
        raise F1BestfitError("closed F1 MCMC endpoints are missing")
    if PLAN.exists():
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        for record in plan["models"].values():
            if sha256_file(ROOT / record["config"]) != record["config_sha256"]:
                raise F1BestfitError("frozen best-fit config changed")
        return plan
    base = yaml_load_file(str(BASE_CONFIG))
    cpl_start, lcdm_start, covariance, names = _starts_and_covariance(base)
    cpl_cov = BESTFIT_ROOT / "cpl/proposal.covmat"
    lcdm_cov = BESTFIT_ROOT / "lcdm/proposal.covmat"
    cpl_record = write_covmat(cpl_cov, names, covariance)
    keep = [i for i, name in enumerate(names) if name not in {"w", "wa"}]
    lcdm_record = write_covmat(lcdm_cov, [names[i] for i in keep], covariance[np.ix_(keep, keep)])
    models = {}
    for model, start, covmat in (("cpl", cpl_start, cpl_cov), ("lcdm", lcdm_start, lcdm_cov)):
        config = BESTFIT_ROOT / model / "bestfit.yaml"
        config.parent.mkdir(parents=True, exist_ok=True)
        config.write_text(yaml_dump(_build_config(model, start, covmat)), encoding="utf-8")
        models[model] = {
            "config": str(config.relative_to(ROOT)), "config_sha256": sha256_file(config),
            "covmat": str(covmat.relative_to(ROOT)), "covmat_sha256": sha256_file(covmat),
            "seed": SEEDS[model], "start": start,
            "start_role": "optimizer initialization only",
        }
    plan = {
        "schema_version": "wp4-f1-bestfit-plan-v1", "status": "FROZEN_BEFORE_OPTIMIZATION",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope_note": "Frozen after MCMC unblinding and before F1 best-fit/model-comparison output.",
        "base_config": str(BASE_CONFIG.relative_to(ROOT)), "base_config_sha256": sha256_file(BASE_CONFIG),
        "mcmc_endpoints": str(ENDPOINTS.relative_to(ROOT)), "mcmc_endpoints_sha256": sha256_file(ENDPOINTS),
        "optimizer": {"implementation": "Cobaya 3.6.2 Py-BOBYQA", "best_of": 1,
                      "max_evals": 2000, "rhoend": 0.05, "ignore_prior": False},
        "parallel_models": 2, "models": models,
        "covariance": {"cpl": cpl_record, "lcdm": lcdm_record,
                       "source": "integer-weighted F1 post-burn posterior"},
        "information_criteria": {
            "delta_definition": "CPL minus LCDM", "delta_k": 2,
            "nominal_data_count": NOMINAL_DATA_COUNT,
            "delta_AIC": "delta_chi2 + 2*delta_k",
            "delta_BIC": "delta_chi2 + delta_k*ln(nominal_data_count)",
            "bic_scope_warning": "descriptive nominal-vector penalty, not evidence",
        },
    }
    atomic_write_json(PLAN, plan)
    return plan


def _environment() -> dict:
    env = os.environ.copy()
    env.update({name: "1" for name in (
        "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
        "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS")})
    env["PYTHONPATH"] = str(ROOT)
    return env


def smoke() -> dict:
    plan = prepare(); records = {}
    for model, record in plan["models"].items():
        result = subprocess.run([str(COBAYA), str(ROOT / record["config"]), "--test", "--no-mpi", "--force"],
                                cwd=ROOT, env=_environment(), text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        log = BESTFIT_ROOT / model / "smoke.log"; log.write_text(result.stdout, encoding="utf-8")
        records[model] = {"returncode": result.returncode, "log": str(log.relative_to(ROOT)),
                          "log_sha256": sha256_file(log),
                          "initialization_success": "Test initialization successful" in result.stdout}
    payload = {"schema_version": "wp4-f1-bestfit-smoke-v1",
               "status": "PASS" if all(x["returncode"] == 0 and x["initialization_success"] for x in records.values()) else "FAIL",
               "created_at_utc": datetime.now(timezone.utc).isoformat(), "models": records,
               "sampling_performed": False, "optimization_performed": False}
    atomic_write_json(SMOKE, payload); return payload


def _run(model: str, record: dict) -> dict:
    config = ROOT / record["config"]; log = config.parent / "bestfit.log"
    started = datetime.now(timezone.utc).isoformat()
    with log.open("w", encoding="utf-8") as stream:
        result = subprocess.run([str(COBAYA), str(config), "--force", "--no-mpi"],
                                cwd=ROOT, env=_environment(), stdout=stream,
                                stderr=subprocess.STDOUT, check=False)
    minimum = config.parent / "bestfit.minimum.txt"
    return {"model": model, "started_at_utc": started,
            "completed_at_utc": datetime.now(timezone.utc).isoformat(),
            "returncode": result.returncode, "log": str(log.relative_to(ROOT)),
            "log_sha256": sha256_file(log), "minimum_present": minimum.is_file(),
            "minimum": str(minimum.relative_to(ROOT)),
            "minimum_sha256": sha256_file(minimum) if minimum.is_file() else None}


def atomic_likelihood_chi2(row: dict) -> tuple[float, dict]:
    aggregates = {"chi2__BAO", "chi2__CMB", "chi2__SN"}
    components = {name: float(value) for name, value in row.items()
                  if name.startswith("chi2__") and name not in aggregates}
    if len(components) != 6:
        raise F1BestfitError(f"expected six atomic likelihoods, got {sorted(components)}")
    return float(sum(components.values())), components


def information_criteria(delta_chi2: float, delta_k: int = 2,
                         nominal_n: int = NOMINAL_DATA_COUNT) -> dict:
    return {"delta_definition": "CPL minus LCDM", "delta_k": delta_k,
            "nominal_data_count": nominal_n, "delta_chi2": delta_chi2,
            "delta_AIC": delta_chi2 + 2 * delta_k,
            "delta_BIC": delta_chi2 + delta_k * math.log(nominal_n)}


def run(jobs: int = 2) -> dict:
    if jobs != 2: raise F1BestfitError("frozen best-fit topology requires two jobs")
    plan = prepare()
    if json.loads(SMOKE.read_text(encoding="utf-8")).get("status") != "PASS":
        raise F1BestfitError("best-fit smoke has not passed")
    if COMPLETION.exists(): return json.loads(COMPLETION.read_text(encoding="utf-8"))
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {model: executor.submit(_run, model, record) for model, record in plan["models"].items()}
        results = {model: future.result() for model, future in futures.items()}
    passed = all(record["returncode"] == 0 and record["minimum_present"] for record in results.values())
    payload = {"schema_version": "wp4-f1-bestfit-completion-v1",
               "status": "PASS" if passed else "FAIL",
               "completed_at_utc": datetime.now(timezone.utc).isoformat(),
               "run_plan": str(PLAN.relative_to(ROOT)), "run_plan_sha256": sha256_file(PLAN),
               "models": results}
    if passed:
        rows = {model: parse_one_point(ROOT / record["minimum"]) for model, record in results.items()}
        atomic = {model: atomic_likelihood_chi2(row) for model, row in rows.items()}
        delta = atomic["cpl"][0] - atomic["lcdm"][0]
        payload["likelihood_chi2"] = {model: {"total": value[0], "components": value[1]}
                                      for model, value in atomic.items()}
        payload["information_criteria"] = information_criteria(delta)
    atomic_write_json(COMPLETION, payload); return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--smoke-only", action="store_true")
    parser.add_argument("--jobs", type=int, default=2)
    args = parser.parse_args()
    result = prepare() if args.prepare_only else smoke() if args.smoke_only else run(args.jobs)
    print(json.dumps({"status": result["status"], "plan": str(PLAN.relative_to(ROOT)),
                      "completion": str(COMPLETION.relative_to(ROOT))}, sort_keys=True))
    return 0 if result["status"] in {"FROZEN_BEFORE_OPTIMIZATION", "PASS"} else 1


if __name__ == "__main__": raise SystemExit(main())
