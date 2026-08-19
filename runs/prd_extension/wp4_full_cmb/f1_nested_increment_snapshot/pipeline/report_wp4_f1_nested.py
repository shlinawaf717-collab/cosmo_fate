#!/usr/bin/env python3
"""Aggregate original-weight and stratified WP4 F1 PolyChord results."""

from __future__ import annotations

import argparse
import json
import math
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import yaml
from scipy.special import logsumexp

from pipeline.fate import Background, classify
from pipeline.prepare_wp4_f1_nested import P1_AREAS, SEEDS, atomic_json


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "runs/prd_extension/wp4_full_cmb/f1_nested"
LABELS = ("CRUNCH", "RIP", "DS", "DECAY", "OTHER")


class F1NestedReportError(RuntimeError):
    """Raised when the 12-run nested campaign is incomplete or inconsistent."""


def _worker(values):
    omegam, H0, w0, wa = values
    return classify(Background(omegam=omegam, H0=H0, w0=w0, wa=wa))[0]


def evidence(path: Path) -> tuple[float, float]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return float(payload["logZ"]), float(payload["logZstd"])


def original_weight_fate(path: Path, jobs: int) -> dict:
    with path.open(encoding="utf-8") as stream: names = stream.readline().lstrip("#").split()
    data = np.loadtxt(path, comments="#", ndmin=2)
    weight = data[:, names.index("weight")].astype(float); weight /= weight.sum()
    args = zip(data[:, names.index("omegam")], data[:, names.index("H0")],
               data[:, names.index("w")], data[:, names.index("wa")])
    with Pool(jobs) as pool: labels = np.asarray(pool.map(_worker, args, chunksize=200))
    probabilities = {label: float(weight[labels == label].sum()) for label in LABELS}
    probabilities["OTHER"] += 1.0 - sum(probabilities.values())
    rip_weight = weight[labels == "RIP"]
    return {"probabilities": probabilities,
            "raw_label_counts": {label: int(np.sum(labels == label)) for label in LABELS},
            "global_weight_ess": float(1.0 / np.sum(weight * weight)),
            "rip_weight_ess": float(rip_weight.sum() ** 2 / np.sum(rip_weight * rip_weight)) if len(rip_weight) else 0.0,
            "weight_sum": float(weight.sum()), "weighted_rows": int(len(weight))}


def summarize_seed(output: Path, plan: dict, seed: int, jobs: int) -> dict:
    records = {row["model"]: row for row in plan["runs"] if row["seed"] == seed}
    values = {}; errors = {}
    for model, record in records.items():
        prefix = ROOT / record["output"]
        raw, error = evidence(prefix.with_suffix(".evidence.yaml"))
        values[model] = raw + float(record["conditional_logZ_correction"])
        errors[model] = error
    log_rip = math.log(P1_AREAS["rip_p1"] / P1_AREAS["p1"]) + values["rip"]
    log_decay = math.log(P1_AREAS["decay_p1"] / P1_AREAS["p1"]) + values["decay"]
    strat_total = float(logsumexp([log_rip, log_decay]))
    p_rip = float(math.exp(log_rip - strat_total))
    full_path = (ROOT / records["cpl"]["output"]).with_suffix(".1.txt")
    original = original_weight_fate(full_path, jobs)
    return {"seed": seed, "corrected_logZ": values, "internal_logZ_errors": errors,
            "lnB_full_CPL_over_LCDM": values["cpl"] - values["lcdm"],
            "lnB_stratified_CPL_over_LCDM": strat_total - values["lcdm"],
            "stratified_logZ_CPL": strat_total,
            "stratified_P_RIP": p_rip,
            "full_vs_stratified_delta_logZ": values["cpl"] - strat_total,
            "original_weight_fate": original}


def report(output: Path, destination: Path, jobs: int) -> dict:
    completion = json.loads((output / "completion.json").read_text(encoding="utf-8"))
    if completion.get("status") != "PASS" or completion.get("completed_runs") != 12:
        raise F1NestedReportError("the 12-run nested campaign is incomplete")
    plan = json.loads((output / "run_plan.json").read_text(encoding="utf-8"))
    runs = [summarize_seed(output, plan, seed, jobs) for seed in SEEDS]
    original = np.asarray([row["original_weight_fate"]["probabilities"]["RIP"] for row in runs])
    strat = np.asarray([row["stratified_P_RIP"] for row in runs])
    lnb = np.asarray([row["lnB_full_CPL_over_LCDM"] for row in runs])
    closure = np.asarray([row["full_vs_stratified_delta_logZ"] for row in runs])
    payload = {"schema_version": "wp4-f1-polychord-multiseed-v1", "status": "PASS",
               "headline_estimators": {"evidence": "mean of corrected full-CPL logZ minus LCDM",
                                       "fate": "original nested weights, with stratified rare-tail verification"},
               "seeds": list(SEEDS), "runs": runs,
               "aggregate": {
                   "P_RIP_original_weight_mean": float(original.mean()),
                   "P_RIP_original_weight_between_seed_sd": float(original.std(ddof=1)),
                   "P_RIP_original_weight_range": [float(original.min()), float(original.max())],
                   "P_RIP_stratified_mean": float(strat.mean()),
                   "P_RIP_stratified_between_seed_sd": float(strat.std(ddof=1)),
                   "P_RIP_stratified_range": [float(strat.min()), float(strat.max())],
                   "lnB_CPL_over_LCDM_mean": float(lnb.mean()),
                   "lnB_CPL_over_LCDM_between_seed_sd": float(lnb.std(ddof=1)),
                   "lnB_CPL_over_LCDM_range": [float(lnb.min()), float(lnb.max())],
                   "full_vs_stratified_delta_logZ": list(map(float, closure)),
               },
               "uncertainty_note": "Per-run PolyChord errors and between-seed variation are reported separately."}
    atomic_json(destination, payload); return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--destination", type=Path)
    parser.add_argument("--jobs", type=int, default=6)
    args = parser.parse_args(); destination = args.destination or args.output_root / "nested_endpoints.json"
    payload = report(args.output_root.resolve(), destination.resolve(), args.jobs)
    print(json.dumps({"status": payload["status"], **payload["aggregate"]}, sort_keys=True))
    return 0


if __name__ == "__main__": raise SystemExit(main())
