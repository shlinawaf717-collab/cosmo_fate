#!/usr/bin/env python3
"""Validate release nested JSON/NPZ pairs without rerunning cosmology."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

try:
    from pipeline import nested_core as nc
except ModuleNotFoundError:  # pragma: no cover - direct script invocation
    import nested_core as nc


ROOT = Path(__file__).resolve().parents[1]
EXTENSION_JSONS = (
    ROOT / "runs/phase3/fdata/nested_d1.json",
    ROOT / "runs/phase3/fdata/nested_d2.json",
    ROOT / "runs/phase3/fdata/nested_d3.json",
    ROOT / "runs/phase3/fdata/nested_d4.json",
    ROOT / "runs/phase3/fparam/nested_cpl_bgw.json",
    ROOT / "runs/phase3/fparam/nested_jbp.json",
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def audit_archive(path: Path, payload: dict, *, require_labels: bool) -> None:
    with np.load(path, allow_pickle=False) as saved:
        required = {
            "samples", "logwt", "weights", "equal_weight_indices", "names",
            "bounds", "logz", "logzerr", "ncall", "schema_version", "seed", "ess",
        }
        missing = required.difference(saved.files)
        if missing:
            raise AssertionError(f"{path}: missing arrays {sorted(missing)}")
        if saved["schema_version"].item() != nc.SCHEMA_VERSION:
            raise AssertionError(f"{path}: stale schema")
        if int(saved["seed"].item()) != int(payload["seed"]):
            raise AssertionError(f"{path}: seed differs from JSON")
        samples = saved["samples"]
        weights = saved["weights"]
        logwt = saved["logwt"]
        names = saved["names"]
        if samples.ndim != 2 or len(samples) == 0:
            raise AssertionError(f"{path}: samples must be a non-empty matrix")
        if len(samples) != len(weights) or len(samples) != len(logwt):
            raise AssertionError(f"{path}: sample/weight/logwt length mismatch")
        if samples.shape[1] != len(names):
            raise AssertionError(f"{path}: parameter-name count mismatch")
        if not np.isclose(weights.sum(), 1.0, rtol=0.0, atol=1e-12):
            raise AssertionError(f"{path}: weights do not sum to one")
        recomputed, ess = nc.stable_normalized_weights(logwt, saved["logz"][-1])
        np.testing.assert_allclose(weights, recomputed, rtol=1e-13, atol=1e-15)
        if not np.isclose(float(saved["ess"]), ess, rtol=1e-12, atol=1e-12):
            raise AssertionError(f"{path}: ESS differs from stored weights")
        if require_labels:
            if "fate_labels" not in saved.files or len(saved["fate_labels"]) != len(samples):
                raise AssertionError(f"{path}: missing or misaligned fate labels")
            probs = nc.probabilities_from_labels(saved["fate_labels"], weights)
            for label in nc.FATE_LABELS:
                if not np.isclose(probs[label], payload["P_fate_weighted"][label],
                                  rtol=0.0, atol=1e-12):
                    raise AssertionError(f"{path}: {label} probability differs from JSON")


def main() -> None:
    seed_payloads = []
    for seed in (1, 2, 3):
        json_path = ROOT / f"runs/phase2/nested_d0_seed{seed}.json"
        payload = load_json(json_path)
        if payload["schema_version"] != nc.SCHEMA_VERSION or payload["seed"] != seed:
            raise AssertionError(f"{json_path}: schema or seed mismatch")
        audit_archive(ROOT / f"runs/phase2/nested_seed{seed}_cpl.npz", payload,
                      require_labels=True)
        audit_archive(ROOT / f"runs/phase2/nested_seed{seed}_lcdm.npz",
                      payload["LCDM_audit"], require_labels=False)
        seed_payloads.append(payload)

    aggregate_path = ROOT / "runs/phase2/nested_d0.json"
    aggregate = load_json(aggregate_path)
    if aggregate["source_schema_version"] != nc.SCHEMA_VERSION:
        raise AssertionError(f"{aggregate_path}: stale source schema")
    if aggregate["seeds"] != [1, 2, 3] or aggregate["n_independent_runs"] != 3:
        raise AssertionError(f"{aggregate_path}: expected independent seeds 1,2,3")
    rebuilt = np.mean([
        [row["P_fate_weighted"][label] for label in nc.FATE_LABELS]
        for row in seed_payloads
    ], axis=0)
    for label, value in zip(nc.FATE_LABELS, rebuilt):
        if not np.isclose(value, aggregate["P_fate_weighted"][label],
                          rtol=0.0, atol=1e-12):
            raise AssertionError(f"{aggregate_path}: {label} aggregate mismatch")

    for json_path in EXTENSION_JSONS:
        payload = load_json(json_path)
        if payload["schema_version"] != nc.SCHEMA_VERSION:
            raise AssertionError(f"{json_path}: stale schema")
        audit_archive(json_path.with_suffix(".npz"), payload, require_labels=True)

    print("nested release archives: PASS (3 D0 seeds, 6 extensions)")


if __name__ == "__main__":
    main()
