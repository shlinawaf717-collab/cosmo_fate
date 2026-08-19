#!/usr/bin/env python3
"""Endpoint-blind two-chain convergence diagnostics for one WP7 SBC dataset."""

from __future__ import annotations

import json
from pathlib import Path

from pipeline.monitor_wp4_f0 import snapshot_chain
from pipeline.monitor_wp7 import NODES, ROOT, _expanded, _node_ess, rank_normalized_split_rhat


SBC_ROOT = ROOT / "runs/prd_extension/wp7/sbc"


def chain_paths(index: int) -> tuple[Path, Path]:
    if not 1 <= int(index) <= 50:
        raise ValueError(index)
    root = SBC_ROOT / f"s{int(index):03d}"
    return root / "c1/chain.1.txt", root / "c2/chain.1.txt"


def collect(index: int) -> dict:
    snapshots = [snapshot_chain(path) for path in chain_paths(index)]
    if snapshots[0].columns != snapshots[1].columns:
        raise ValueError("SBC chain headers differ")
    rhat, bulk, tail = {}, {}, {}
    for name in NODES:
        arrays = [_expanded(snapshot, name) for snapshot in snapshots]
        rhat[name] = rank_normalized_split_rhat(arrays)
        bulk[name], tail[name] = _node_ess(arrays)
    gates = {
        "all_node_rhat_lt_1p01": max(rhat.values()) < 1.01,
        "all_node_bulk_ess_gt_400": min(bulk.values()) > 400,
        "all_node_tail_ess_gt_400": min(tail.values()) > 400,
    }
    return {
        "schema_version": "wp7-fs7-sbc-convergence-monitor-v1",
        "dataset_index": int(index),
        "status": "PASS" if all(gates.values()) else "CONTINUE",
        "chain_snapshots": [{"path": snapshot.path, "rows": int(len(snapshot.data)), "sha256": snapshot.sha256, "captured_bytes": snapshot.captured_bytes} for snapshot in snapshots],
        "rhat_by_node": rhat,
        "bulk_ess_by_node": bulk,
        "tail_ess_by_node": tail,
        "gates": gates,
        "truth_rank_calculated": False,
        "fate_endpoint_calculated": False,
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(); parser.add_argument("index", type=int); args = parser.parse_args()
    result = collect(args.index)
    print(json.dumps({"index": args.index, "status": result["status"], "rows": [row["rows"] for row in result["chain_snapshots"]], "gates": result["gates"]}, sort_keys=True))
