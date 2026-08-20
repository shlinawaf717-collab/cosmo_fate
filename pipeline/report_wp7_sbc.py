#!/usr/bin/env python3
"""Produce the frozen WP7 SBC rank and coverage audit after 50/50 closure."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np
from scipy.stats import binom, kstest

from pipeline.audit_wp4_f0_reproduction import atomic_write_json
from pipeline.monitor_wp7 import NODES, ROOT


SBC_ROOT = ROOT / "runs/prd_extension/wp7/sbc"
OUTPUT = SBC_ROOT / "sbc_report.json"
RANKS_CSV = SBC_ROOT / "sbc_ranks.csv"
DATASETS = 50
POSTERIOR_DRAWS = 400
ALPHA = 0.05


def _posterior_nodes(index: int) -> tuple[np.ndarray, np.ndarray]:
    values, weights = [], []
    for chain in (1, 2):
        path = SBC_ROOT / f"s{index:03d}/c{chain}/chain.1.txt"
        with path.open() as stream:
            columns = stream.readline().lstrip("#").split()
        data = np.loadtxt(path, ndmin=2)
        data = data[int(0.5 * len(data)):]
        raw_weights = data[:, columns.index("weight")]
        integer = np.rint(raw_weights).astype(np.int64)
        if np.any(integer <= 0) or not np.allclose(raw_weights, integer):
            raise RuntimeError(f"s{index:03d} c{chain}: invalid weights")
        values.append(data[:, [columns.index(name) for name in NODES]])
        weights.append(integer)
    return np.concatenate(values), np.concatenate(weights)


def systematic_resample(values: np.ndarray, weights: np.ndarray, count: int, seed: int) -> np.ndarray:
    probabilities = np.asarray(weights, dtype=float); probabilities /= probabilities.sum()
    cumulative = np.cumsum(probabilities); cumulative[-1] = 1.0
    rng = np.random.default_rng(seed)
    positions = (rng.random() + np.arange(count)) / count
    return values[np.searchsorted(cumulative, positions, side="right")]


def holm_rejections(pvalues: dict[str, float], alpha: float = ALPHA) -> dict[str, bool]:
    ordered = sorted(pvalues, key=pvalues.get)
    rejected = {name: False for name in pvalues}
    for rank, name in enumerate(ordered):
        threshold = alpha / (len(ordered) - rank)
        if pvalues[name] <= threshold:
            rejected[name] = True
        else:
            break
    return rejected


def exact_acceptance_interval(n: int, probability: float, alpha: float = ALPHA) -> tuple[int, int]:
    return int(binom.ppf(alpha / 2.0, n, probability)), int(binom.ppf(1.0 - alpha / 2.0, n, probability))


def report() -> dict:
    rank_rows = []
    coverage = {name: {"0.5": 0, "0.9": 0} for name in NODES}
    for index in range(1, DATASETS + 1):
        audit = SBC_ROOT / f"s{index:03d}/convergence_audit.json"
        if not audit.is_file() or json.loads(audit.read_text()).get("status") != "PASS":
            raise RuntimeError(f"s{index:03d}: convergence audit is not PASS")
        truth = np.asarray(json.loads((SBC_ROOT / f"s{index:03d}/truth.json").read_text())["fs7_nodes"])
        values, weights = _posterior_nodes(index)
        draws = systematic_resample(values, weights, POSTERIOR_DRAWS, 2026110000 + index)
        row = {"dataset_index": index}
        for node_index, name in enumerate(NODES, 1):
            less = int(np.count_nonzero(draws[:, node_index - 1] < truth[node_index - 1]))
            equal = int(np.count_nonzero(draws[:, node_index - 1] == truth[node_index - 1]))
            rng = np.random.default_rng(2026120000 + 10 * index + node_index)
            integer_rank = less + (int(rng.integers(0, equal + 1)) if equal else 0)
            normalized = (integer_rank + rng.random()) / (POSTERIOR_DRAWS + 1.0)
            row[name] = normalized
            q25, q75 = np.quantile(draws[:, node_index - 1], (0.25, 0.75))
            q05, q95 = np.quantile(draws[:, node_index - 1], (0.05, 0.95))
            coverage[name]["0.5"] += int(q25 <= truth[node_index - 1] <= q75)
            coverage[name]["0.9"] += int(q05 <= truth[node_index - 1] <= q95)
        rank_rows.append(row)
    with RANKS_CSV.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=("dataset_index", *NODES)); writer.writeheader(); writer.writerows(rank_rows)
    pvalues = {name: float(kstest([row[name] for row in rank_rows], "uniform").pvalue) for name in NODES}
    rejected = holm_rejections(pvalues)
    coverage_intervals = {probability: exact_acceptance_interval(DATASETS, float(probability)) for probability in ("0.5", "0.9")}
    coverage_gates = {name: {probability: coverage_intervals[probability][0] <= count <= coverage_intervals[probability][1] for probability, count in counts.items()} for name, counts in coverage.items()}
    gates = {
        "all_50_converged": True,
        "no_holm_adjusted_rank_rejection": not any(rejected.values()),
        "all_50pct_coverage_counts_accepted": all(row["0.5"] for row in coverage_gates.values()),
        "all_90pct_coverage_counts_accepted": all(row["0.9"] for row in coverage_gates.values()),
    }
    payload = {
        "schema_version": "wp7-fs7-sbc-report-v1",
        "status": "PASS" if all(gates.values()) else "FAIL",
        "datasets": DATASETS, "posterior_draws_per_dataset": POSTERIOR_DRAWS,
        "rank_uniformity": {"ks_pvalues": pvalues, "holm_alpha": ALPHA, "rejected": rejected},
        "coverage": {"counts": coverage, "exact_95pct_acceptance_intervals": coverage_intervals, "gates": coverage_gates},
        "gates": gates,
        "fate_endpoint_calculated": False,
    }
    atomic_write_json(OUTPUT, payload); return payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.parse_args()
    result = report(); print(json.dumps({"status": result["status"], "gates": result["gates"]}, sort_keys=True)); raise SystemExit(0 if result["status"] == "PASS" else 1)
