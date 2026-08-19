#!/usr/bin/env python3
"""Blinded rank-Rhat/ESS monitor for one four-chain WP7 setting."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence

import numpy as np
from scipy.stats import norm, rankdata

from pipeline.monitor_wp4_f0 import ChainSnapshot, _split_ess, snapshot_chain


ROOT = Path(__file__).resolve().parents[1]
SYSTEM = ROOT / "runs/prd_extension/wp7/production_system"
SETTINGS = ("primary", "sig025", "sig100", "ell035", "ell140")
SAMPLED = ("ombh2", "omegam", "H0", "Mb", "z1", "z2", "z3", "z4", "z5", "z6", "z7")
NODES = tuple(f"fs7_w{i}" for i in range(1, 8))
ALL_GATED = (*SAMPLED, *NODES)
BURN = 0.5
BATCHES_PER_CHAIN = 32


def chain_paths(setting: str, root: Path = SYSTEM) -> tuple[Path, ...]:
    if setting not in SETTINGS:
        raise ValueError(setting)
    return tuple(root / setting / f"c{i}/chain.1.txt" for i in range(1, 5))


def _expanded(snapshot: ChainSnapshot, name: str, burn: float = BURN) -> np.ndarray:
    index = {column: i for i, column in enumerate(snapshot.columns)}
    if name not in index or "weight" not in index:
        raise ValueError(f"missing {name} or weight in {snapshot.path}")
    selected = snapshot.data[int(len(snapshot.data) * burn):]
    weights = np.rint(selected[:, index["weight"]]).astype(np.int64)
    if np.any(weights <= 0) or not np.allclose(selected[:, index["weight"]], weights):
        raise ValueError(f"invalid integer weights in {snapshot.path}")
    return np.repeat(selected[:, index[name]], weights)


def _split_equalized(arrays: Sequence[np.ndarray]) -> np.ndarray:
    common = min(len(array) for array in arrays)
    half = common // 2
    if half < 20:
        raise ValueError("too few equalized post-burn draws")
    usable = 2 * half
    return np.asarray([
        segment
        for array in arrays
        for segment in (array[-usable:-half], array[-half:])
    ])


def _basic_rhat(split: np.ndarray) -> float:
    chains, draws = split.shape
    within = float(np.mean(np.var(split, axis=1, ddof=1)))
    between = float(draws * np.var(np.mean(split, axis=1), ddof=1))
    if within <= 0:
        return 1.0 if between == 0 else np.inf
    variance = (draws - 1.0) / draws * within + between / draws
    return float(np.sqrt(variance / within))


def rank_normalized_split_rhat(arrays: Sequence[np.ndarray]) -> float:
    split = _split_equalized(arrays)
    flat = split.ravel()
    ranks = rankdata(flat, method="average")
    bulk = norm.ppf((ranks - 0.375) / (flat.size + 0.25)).reshape(split.shape)
    folded_values = np.abs(flat - np.median(flat))
    folded_ranks = rankdata(folded_values, method="average")
    folded = norm.ppf((folded_ranks - 0.375) / (flat.size + 0.25)).reshape(split.shape)
    return max(_basic_rhat(bulk), _basic_rhat(folded))


def _node_ess(arrays: Sequence[np.ndarray]) -> tuple[float, float]:
    split = _split_equalized(arrays)
    flat = split.ravel()
    ranks = rankdata(flat, method="average")
    normalized = norm.ppf((ranks - 0.375) / (flat.size + 0.25)).reshape(split.shape)
    bulk = _split_ess(normalized)
    q05, q95 = np.quantile(flat, (0.05, 0.95))
    tail = min(
        _split_ess((split <= q05).astype(float)),
        _split_ess((split >= q95).astype(float)),
    )
    return bulk, tail


def _hidden_sign_mcse_pass(arrays: Sequence[np.ndarray], threshold: float = 0.01) -> bool:
    common = min(len(array) for array in arrays)
    usable = common - common % BATCHES_PER_CHAIN
    if usable < BATCHES_PER_CHAIN * 10:
        return False
    means = []
    for array in arrays:
        indicator = (array[-usable:] < -1.0).astype(float)
        means.extend(block.mean() for block in np.split(indicator, BATCHES_PER_CHAIN))
    mcse = float(np.std(means, ddof=1) / np.sqrt(len(means)))
    return mcse < threshold


def collect(setting: str, paths: Sequence[Path] | None = None) -> dict:
    snapshots = [snapshot_chain(path) for path in (paths or chain_paths(setting))]
    if any(snapshot.columns != snapshots[0].columns for snapshot in snapshots[1:]):
        raise ValueError("WP7 chain headers differ")
    arrays = {name: [_expanded(snapshot, name) for snapshot in snapshots] for name in ALL_GATED}
    rhat = {name: rank_normalized_split_rhat(values) for name, values in arrays.items()}
    bulk, tail = {}, {}
    for name in NODES:
        bulk[name], tail[name] = _node_ess(arrays[name])
    gates = {
        "all_parameter_rhat_lt_1p01": max(rhat.values()) < 1.01,
        "all_node_bulk_ess_gt_400": min(bulk.values()) > 400,
        "all_node_tail_ess_gt_400": min(tail.values()) > 400,
        "hidden_final_sign_mcse_lt_0p01": _hidden_sign_mcse_pass(arrays["fs7_w7"]),
    }
    return {
        "schema_version": "wp7-fs7-blinded-monitor-v1",
        "setting": setting,
        "status": "CANDIDATE_PASS" if all(gates.values()) else "CANDIDATE_CONTINUE",
        "chain_snapshots": [{
            "path": snapshot.path,
            "rows": int(snapshot.data.shape[0]),
            "total_weight": int(np.rint(snapshot.data[:, snapshot.columns.index("weight")]).sum()),
            "captured_bytes": snapshot.captured_bytes,
            "sha256": snapshot.sha256,
        } for snapshot in snapshots],
        "rhat": {"definition": "maximum rank-normalized split and folded-split R-hat", "by_parameter": rhat},
        "ess": {"definition": "rank-normalized split bulk and binary 5/95-percent tail ESS", "bulk_by_node": bulk, "tail_by_node": tail},
        "candidate_gates": gates,
        "blinding": {"locations": False, "intervals": False, "likelihoods": False, "sign_probability": False, "fate": False},
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("setting", choices=SETTINGS)
    args = parser.parse_args()
    result = collect(args.setting)
    print(json.dumps({
        "status": result["status"], "setting": args.setting,
        "rows": [row["rows"] for row in result["chain_snapshots"]],
        "max_rhat": max(result["rhat"]["by_parameter"].values()),
        "min_bulk_ess": min(result["ess"]["bulk_by_node"].values()),
        "min_tail_ess": min(result["ess"]["tail_by_node"].values()),
        "gates": result["candidate_gates"],
    }, sort_keys=True))
