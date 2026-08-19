#!/usr/bin/env python3
"""Generate versioned posterior and fate endpoints from the closed WSL2 F1 chains."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from multiprocessing import Pool
from pathlib import Path

import numpy as np

from pipeline.fate import Background, THERMO, classify
from pipeline.monitor_wp4_f1 import collect_diagnostics


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUN = ROOT / "runs/prd_extension/wp4_full_cmb/f1_wsl2"
LABELS = ("CRUNCH", "RIP", "DS", "DECAY", "OTHER")
POSTERIOR_PARAMETERS = (
    "w", "wa", "omegam", "H0", "Mb", "ombh2", "omch2", "ns", "tau", "sigma8"
)
BURN_FRACTION = 0.5
BATCHES = 32


class F1EndpointError(RuntimeError):
    """Raised when closed-chain endpoints cannot be reported safely."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush(); os.fsync(handle.fileno()); temporary = Path(handle.name)
    os.replace(temporary, path)


def weighted_quantile(values: np.ndarray, weights: np.ndarray, probabilities) -> np.ndarray:
    order = np.argsort(values)
    values = np.asarray(values, dtype=float)[order]
    weights = np.asarray(weights, dtype=float)[order]
    if np.any(weights <= 0) or weights.sum() <= 0:
        raise F1EndpointError("quantile weights must be positive")
    positions = (np.cumsum(weights) - 0.5 * weights) / weights.sum()
    return np.interp(np.asarray(probabilities, dtype=float), positions, values)


def _classify_worker(values):
    omegam, H0, w0, wa = values
    return classify(Background(omegam=omegam, H0=H0, w0=w0, wa=wa))


def _load_chains(run_root: Path) -> tuple[list[dict], list[np.ndarray], list[np.ndarray]]:
    chains = []; selected = []; weights = []
    expected = json.loads((run_root / "ingest_audit.json").read_text(encoding="utf-8"))["chains"]
    for ordinal in range(1, 5):
        path = run_root / f"raw/work/f1/c{ordinal}/chain.1.txt"
        with path.open(encoding="utf-8") as stream:
            columns = stream.readline().lstrip("#").split()
        data = np.loadtxt(path, comments="#", ndmin=2)
        record = expected[ordinal - 1]
        if sha256_file(path) != record["sha256"] or data.shape[0] != record["rows"]:
            raise F1EndpointError(f"ingested chain identity mismatch: c{ordinal}")
        first = int(data.shape[0] * BURN_FRACTION)
        post = data[first:]
        index = {name: i for i, name in enumerate(columns)}
        missing = set(("weight", *POSTERIOR_PARAMETERS)).difference(index)
        if missing:
            raise F1EndpointError(f"missing columns in c{ordinal}: {sorted(missing)}")
        weight = post[:, index["weight"]]
        if np.any(weight <= 0) or not np.allclose(weight, np.rint(weight)):
            raise F1EndpointError(f"invalid weights in c{ordinal}")
        if np.any(post[:, index["w"]] + post[:, index["wa"]] >= 0):
            raise F1EndpointError(f"P1 violation in c{ordinal}")
        selected.append(post)
        weights.append(weight)
        chains.append({
            "chain": ordinal, "path": str(path.relative_to(ROOT)), "full_rows": int(data.shape[0]),
            "post_burn_rows": int(post.shape[0]), "post_burn_weight": int(np.rint(weight).sum()),
            "sha256": record["sha256"], "columns": columns,
        })
    if any(chain["columns"] != chains[0]["columns"] for chain in chains[1:]):
        raise F1EndpointError("chain headers differ")
    return chains, selected, weights


def _posterior(chains: list[dict], selected: list[np.ndarray], weights: list[np.ndarray]) -> dict:
    columns = chains[0]["columns"]
    data = np.concatenate(selected); weight = np.concatenate(weights)
    result = {}
    for name in POSTERIOR_PARAMETERS:
        values = data[:, columns.index(name)]
        mean = float(np.average(values, weights=weight))
        sd = float(np.sqrt(np.average((values - mean) ** 2, weights=weight)))
        q = weighted_quantile(values, weight, (0.025, 0.16, 0.5, 0.84, 0.975))
        result[name] = {
            "mean": mean, "sd": sd, "q2p5": float(q[0]), "q16": float(q[1]),
            "median": float(q[2]), "q84": float(q[3]), "q97p5": float(q[4]),
        }
    return {
        "estimator": "integer-weighted population mean, SD, and weighted quantiles",
        "row_burn_fraction_per_chain": BURN_FRACTION,
        "post_burn_rows": int(data.shape[0]),
        "post_burn_weight": int(np.rint(weight).sum()),
        "parameters": result,
    }


def _fate(chains: list[dict], selected: list[np.ndarray], weights: list[np.ndarray], jobs: int) -> dict:
    columns = chains[0]["columns"]
    args = []
    for data in selected:
        args.extend(zip(
            data[:, columns.index("omegam")], data[:, columns.index("H0")],
            data[:, columns.index("w")], data[:, columns.index("wa")],
        ))
    with Pool(processes=jobs) as pool:
        classified = pool.map(_classify_worker, args, chunksize=200)
    labels = np.asarray([item[0] for item in classified])
    boundaries = np.asarray([item[1] for item in classified], dtype=bool)
    weight = np.concatenate(weights)
    wa = np.concatenate([data[:, columns.index("wa")] for data in selected])
    total = float(weight.sum())
    probabilities = {}; raw_rows = {}; weighted_mass = {}; mc_error = {}
    edges = np.linspace(0, len(weight), BATCHES + 1, dtype=int)
    for label in LABELS:
        indicator = labels == label
        weighted = float(weight[indicator].sum())
        blocks = []
        for lo, hi in zip(edges[:-1], edges[1:]):
            block_weight = weight[lo:hi]
            blocks.append(float((block_weight * indicator[lo:hi]).sum() / block_weight.sum()))
        probabilities[label] = weighted / total
        raw_rows[label] = int(indicator.sum())
        weighted_mass[label] = weighted
        mc_error[label] = float(np.std(blocks, ddof=1) / np.sqrt(BATCHES))
    per_chain = []
    offset = 0
    for chain, data, chain_weight in zip(chains, selected, weights):
        stop = offset + len(data); indicator = labels[offset:stop] == "RIP"
        per_chain.append({
            "chain": chain["chain"], "raw_rip_rows": int(indicator.sum()),
            "rip_weight": float(chain_weight[indicator].sum()),
            "P_RIP": float(chain_weight[indicator].sum() / chain_weight.sum()),
        })
        offset = stop
    p_rip = probabilities["RIP"]
    return {
        "classifier": "pipeline.fate.Background/classify, every post-burn row",
        "classes": {
            label: {"P": probabilities[label], "mc_error_batch_means": mc_error[label],
                    "raw_rows": raw_rows[label], "weighted_mass": weighted_mass[label],
                    "thermodynamic_class": THERMO[label]}
            for label in LABELS
        },
        "boundary_fraction": float(weight[boundaries].sum() / total),
        "boundary_raw_rows": int(boundaries.sum()),
        "P_heat_death_compatible": probabilities["DS"] + probabilities["DECAY"],
        "P_non_heat_death": probabilities["RIP"] + probabilities["CRUNCH"],
        "rip_equals_positive_wa_weight": bool(
            np.array_equal(labels == "RIP", wa > 0)
        ),
        "per_chain_rip": per_chain,
        "tail_audit": {
            "threshold_requiring_nested_verification": 0.01,
            "P_RIP_below_threshold": p_rip < 0.01,
            "nested_verification_required": p_rip < 0.01,
            "sparse_mcmc_tail": raw_rows["RIP"] < 20,
            "interpretation": "MCMC tail is provisional until registered multi-seed nested verification.",
        },
    }


def report(run_root: Path, output: Path, jobs: int) -> dict:
    ingest = json.loads((run_root / "ingest_audit.json").read_text(encoding="utf-8"))
    if ingest.get("status") != "PASS":
        raise F1EndpointError("WSL2 ingest audit has not passed")
    chains, selected, weights = _load_chains(run_root)
    chain_paths = [run_root / f"raw/work/f1/c{i}/chain.1.txt" for i in range(1, 5)]
    convergence = collect_diagnostics(chain_paths)
    gates = {
        "rminus1_primary": convergence["rminus1"]["by_burn_fraction"]["0.5"] < 0.01,
        "rminus1_sensitivity": all(convergence["rminus1"]["by_burn_fraction"][key] < 0.02 for key in ("0.2", "0.7")),
        "bulk_ess_w_wa": all(convergence["ess"]["bulk_by_parameter"][name] > 1000 for name in ("w", "wa")),
        "tail_ess_w_wa": all(convergence["ess"]["tail_by_parameter"][name] > 400 for name in ("w", "wa")),
    }
    if not all(gates.values()):
        raise F1EndpointError(f"independent convergence failed: {gates}")
    payload = {
        "schema_version": "wp4-f1-mcmc-endpoints-v1",
        "status": "PASS_MCMC_NESTED_VERIFICATION_REQUIRED",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_ingest_audit": str((run_root / "ingest_audit.json").relative_to(ROOT)),
        "source_ingest_audit_sha256": sha256_file(run_root / "ingest_audit.json"),
        "chains": [{key: value for key, value in chain.items() if key != "columns"} for chain in chains],
        "convergence": {
            "gates": gates, "rminus1": convergence["rminus1"], "ess": convergence["ess"],
            "independent_chain_sha256": [item["sha256"] for item in convergence["chain_snapshots"]],
        },
        "posterior": _posterior(chains, selected, weights),
        "fate": _fate(chains, selected, weights, jobs),
        "model_comparison": {"status": "PENDING_F1_BESTFITS_AND_MULTI_SEED_NESTED"},
    }
    atomic_json(output, payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, default=DEFAULT_RUN)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--jobs", type=int, default=4)
    args = parser.parse_args()
    output = args.output or args.run_root / "mcmc_endpoints.json"
    payload = report(args.run_root.resolve(), output.resolve(), args.jobs)
    print(json.dumps({
        "status": payload["status"], "P_RIP": payload["fate"]["classes"]["RIP"]["P"],
        "output": str(output),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
