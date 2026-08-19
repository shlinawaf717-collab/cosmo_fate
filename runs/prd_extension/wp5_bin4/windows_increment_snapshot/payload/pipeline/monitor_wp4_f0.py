#!/usr/bin/env python3
"""Read-only convergence diagnostics for the running WP4 F0 chains.

This first version is deliberately non-authoritative: it cannot signal or stop
the sampler.  It reports only chain sizes, hashes, multivariate R-1, ESS, and
candidate gate status.  It never reports posterior locations, intervals,
best-fit points, likelihood values, or fate quantities.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

import numpy as np
from cobaya.functions import inverse_cholesky
from scipy.stats import norm, rankdata


SCHEMA_VERSION = "wp4-f0-read-only-monitor-v1"
SAMPLED_PARAMETERS = (
    "logA",
    "ns",
    "theta_MC_100",
    "ombh2",
    "omch2",
    "tau",
    "w",
    "wa",
    "A_planck",
    "amp_143",
    "amp_217",
    "amp_143x217",
    "n_143",
    "n_217",
    "n_143x217",
    "calTE",
    "calEE",
)
DEFAULT_CHAIN_PATHS = tuple(
    Path(f"runs/prd_extension/wp4_full_cmb/f0/c{i}/chain.1.txt")
    for i in range(1, 5)
)
DEFAULT_BURNS = (0.2, 0.5, 0.7)
PRIMARY_BURN = 0.5


@dataclass(frozen=True)
class ChainSnapshot:
    path: str
    captured_bytes: int
    file_size_at_open: int
    mtime_ns_at_open: int
    sha256: str
    columns: tuple[str, ...]
    data: np.ndarray


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _complete_prefix(raw: bytes) -> bytes:
    """Return only newline-terminated records from a possibly growing file."""
    last_newline = raw.rfind(b"\n")
    if last_newline < 0:
        return b""
    return raw[: last_newline + 1]


def snapshot_chain(path: Path) -> ChainSnapshot:
    """Read one immutable byte prefix without locking or modifying the chain."""
    with path.open("rb") as handle:
        stat_at_open = os.fstat(handle.fileno())
        raw = handle.read(stat_at_open.st_size)
    complete = _complete_prefix(raw)
    if not complete:
        raise ValueError(f"no complete records in {path}")
    first_line = complete.splitlines()[0].decode("utf-8")
    if not first_line.lstrip().startswith("#"):
        raise ValueError(f"missing Cobaya header in {path}")
    columns = tuple(first_line.lstrip()[1:].split())
    data = np.loadtxt(io.BytesIO(complete), comments="#", ndmin=2)
    if data.shape[1] != len(columns):
        raise ValueError(
            f"column mismatch in {path}: header={len(columns)}, data={data.shape[1]}"
        )
    return ChainSnapshot(
        path=str(path),
        captured_bytes=len(complete),
        file_size_at_open=stat_at_open.st_size,
        mtime_ns_at_open=stat_at_open.st_mtime_ns,
        sha256=hashlib.sha256(complete).hexdigest(),
        columns=columns,
        data=data,
    )


def _parameter_arrays(
    snapshots: Sequence[ChainSnapshot],
    burn_fraction: float,
) -> tuple[list[np.ndarray], list[np.ndarray], list[int]]:
    if not 0 <= burn_fraction < 1:
        raise ValueError("burn fraction must be in [0, 1)")
    values: list[np.ndarray] = []
    weights: list[np.ndarray] = []
    row_counts: list[int] = []
    for snapshot in snapshots:
        index = {name: i for i, name in enumerate(snapshot.columns)}
        missing = set(("weight", *SAMPLED_PARAMETERS)).difference(index)
        if missing:
            raise ValueError(f"missing columns in {snapshot.path}: {sorted(missing)}")
        first = int(snapshot.data.shape[0] * burn_fraction)
        selected = snapshot.data[first:]
        if selected.shape[0] < 3:
            raise ValueError(f"too few post-burn rows in {snapshot.path}")
        raw_weights = selected[:, index["weight"]]
        integer_weights = np.rint(raw_weights).astype(np.int64)
        if np.any(integer_weights <= 0) or not np.allclose(
            raw_weights, integer_weights
        ):
            raise ValueError(f"non-positive or non-integer weights in {snapshot.path}")
        values.append(
            selected[:, [index[name] for name in SAMPLED_PARAMETERS]].astype(
                np.float64, copy=False
            )
        )
        weights.append(integer_weights)
        row_counts.append(selected.shape[0])
    return values, weights, row_counts


def cobaya_multivariate_rminus1(
    snapshots: Sequence[ChainSnapshot], burn_fraction: float
) -> float:
    """Reproduce Cobaya's MPI-chain multivariate R-1 calculation."""
    values, weights, row_counts = _parameter_arrays(snapshots, burn_fraction)
    means = np.asarray(
        [np.average(x, axis=0, weights=w) for x, w in zip(values, weights)]
    )
    covariances = np.asarray(
        [np.cov(x.T, ddof=0, fweights=w) for x, w in zip(values, weights)]
    )
    mean_of_covs = np.average(covariances, weights=row_counts, axis=0)
    cov_of_means = np.atleast_2d(np.cov(means.T))
    diagonal = np.sqrt(np.diag(cov_of_means))
    if np.any(~np.isfinite(diagonal)) or np.any(diagonal <= 0):
        raise ValueError("degenerate between-chain covariance")
    corr_of_means = (cov_of_means / diagonal).T / diagonal
    normalized_within = (mean_of_covs / diagonal).T / diagonal
    linv = inverse_cholesky(normalized_within)
    eigenvalues = np.linalg.eigvalsh(linv @ corr_of_means @ linv.T)
    return float(np.max(np.abs(eigenvalues)))


def _autocovariance(sequence: np.ndarray) -> np.ndarray:
    sequence = np.asarray(sequence, dtype=np.float64)
    n = sequence.size
    centered = sequence - np.mean(sequence)
    fft_length = 1 << (2 * n - 1).bit_length()
    transformed = np.fft.rfft(centered, n=fft_length)
    return np.fft.irfft(transformed * np.conjugate(transformed), n=fft_length)[
        :n
    ].real / n


def _split_ess(split_chains: np.ndarray) -> float:
    """Geyer initial-positive, initial-monotone split-chain ESS."""
    split_chains = np.asarray(split_chains, dtype=np.float64)
    if split_chains.ndim != 2:
        raise ValueError("split chains must be a 2-D array")
    chain_count, draw_count = split_chains.shape
    if chain_count < 2 or draw_count < 3:
        raise ValueError("too few split-chain draws for ESS")
    autocov = np.asarray([_autocovariance(chain) for chain in split_chains])
    within = float(np.mean(np.var(split_chains, axis=1, ddof=1)))
    between = float(np.var(np.mean(split_chains, axis=1), ddof=1))
    var_plus = within * (draw_count - 1) / draw_count + between
    total = chain_count * draw_count
    if not np.isfinite(var_plus) or var_plus <= 0:
        return float(total)
    rho = np.ones(draw_count, dtype=np.float64)
    for lag in range(1, draw_count):
        rho[lag] = 1.0 - (within - float(np.mean(autocov[:, lag]))) / var_plus
    paired: list[float] = []
    for even in range(0, draw_count - 1, 2):
        pair = float(rho[even] + rho[even + 1])
        if pair < 0:
            break
        if paired:
            pair = min(pair, paired[-1])
        paired.append(pair)
    tau = -1.0 + 2.0 * float(np.sum(paired))
    tau = max(tau, 1.0 / math.log10(total))
    return float(min(total / tau, total))


def _expanded_equalized_split(
    values: Sequence[np.ndarray],
    weights: Sequence[np.ndarray],
    parameter_index: int,
) -> np.ndarray:
    expanded = [
        np.repeat(chain[:, parameter_index], chain_weights)
        for chain, chain_weights in zip(values, weights)
    ]
    common = min(array.size for array in expanded)
    half = common // 2
    if half < 3:
        raise ValueError("too few weighted draws for split ESS")
    usable = 2 * half
    return np.asarray(
        [
            segment
            for array in expanded
            for segment in (array[-usable:-half], array[-half:])
        ],
        dtype=np.float64,
    )


def rank_normalized_ess(
    snapshots: Sequence[ChainSnapshot], burn_fraction: float
) -> tuple[dict[str, float], dict[str, float], int]:
    """Return rank-normalized bulk and 5%/95% tail split ESS."""
    values, weights, _ = _parameter_arrays(snapshots, burn_fraction)
    bulk: dict[str, float] = {}
    tail: dict[str, float] = {}
    equalized_draws = 0
    for parameter_index, name in enumerate(SAMPLED_PARAMETERS):
        split = _expanded_equalized_split(values, weights, parameter_index)
        equalized_draws = split.size
        flat = split.ravel()
        ranks = rankdata(flat, method="average")
        normalized = norm.ppf((ranks - 0.375) / (flat.size + 0.25)).reshape(
            split.shape
        )
        bulk[name] = _split_ess(normalized)
        q05, q95 = np.quantile(flat, (0.05, 0.95))
        low = _split_ess((split <= q05).astype(np.float64))
        high = _split_ess((split >= q95).astype(np.float64))
        tail[name] = min(low, high)
    return bulk, tail, equalized_draws


def collect_diagnostics(
    chain_paths: Sequence[Path],
    burn_fractions: Sequence[float] = DEFAULT_BURNS,
    primary_burn: float = PRIMARY_BURN,
) -> dict:
    started = _utc_now()
    snapshots = [snapshot_chain(path) for path in chain_paths]
    if any(snapshot.columns != snapshots[0].columns for snapshot in snapshots[1:]):
        raise ValueError("chain headers differ")
    rminus1 = {
        f"{burn:.1f}": cobaya_multivariate_rminus1(snapshots, burn)
        for burn in burn_fractions
    }
    bulk, tail, equalized_draws = rank_normalized_ess(snapshots, primary_burn)
    primary_r = rminus1[f"{primary_burn:.1f}"]
    gates = {
        "rminus1_17d_burn_0p5_lt_0p01": primary_r < 0.01,
        "bulk_ess_all_17_gt_1000": min(bulk.values()) > 1000,
        "tail_ess_w_wa_gt_400": min(tail["w"], tail["wa"]) > 400,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "captured_at_start_utc": started,
        "captured_at_end_utc": _utc_now(),
        "decision_authority": False,
        "sampler_signal_capability": False,
        "status": "CANDIDATE_PASS" if all(gates.values()) else "CANDIDATE_CONTINUE",
        "chain_snapshots": [
            {
                "path": snapshot.path,
                "rows": int(snapshot.data.shape[0]),
                "total_weight": int(
                    np.rint(
                        snapshot.data[:, snapshot.columns.index("weight")]
                    ).sum()
                ),
                "captured_bytes": snapshot.captured_bytes,
                "file_size_at_open": snapshot.file_size_at_open,
                "mtime_ns_at_open": snapshot.mtime_ns_at_open,
                "sha256": snapshot.sha256,
            }
            for snapshot in snapshots
        ],
        "rminus1": {
            "definition": "Cobaya 3.6.2 MPI-chain multivariate, 17 sampled parameters",
            "by_burn_fraction": rminus1,
        },
        "ess": {
            "definition": "rank-normalized split bulk ESS and binary 5%/95% tail ESS",
            "primary_burn_fraction": primary_burn,
            "equalized_split_draws_total": equalized_draws,
            "bulk_by_parameter": bulk,
            "tail_by_parameter": tail,
        },
        "candidate_gates": gates,
        "blinding": {
            "posterior_locations_reported": False,
            "posterior_intervals_reported": False,
            "best_fit_reported": False,
            "likelihood_values_reported": False,
            "fate_quantities_reported": False,
        },
    }


def _atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        temporary = Path(handle.name)
    os.replace(temporary, path)


def _append_jsonl(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    try:
        os.write(descriptor, line.encode("utf-8"))
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _emit(payload: dict, output_dir: Path | None) -> None:
    if output_dir is not None:
        _atomic_json(output_dir / "latest.json", payload)
        _append_jsonl(output_dir / "diagnostics.jsonl", payload)
    print(json.dumps(payload, indent=2, sort_keys=True), flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--chain",
        action="append",
        type=Path,
        dest="chains",
        help="chain path; repeat four times (defaults to WP4 F0 c1..c4)",
    )
    parser.add_argument(
        "--burn-fractions",
        nargs="+",
        type=float,
        default=list(DEFAULT_BURNS),
    )
    parser.add_argument("--primary-burn", type=float, default=PRIMARY_BURN)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--interval-seconds", type=float, default=1800.0)
    args = parser.parse_args()
    chain_paths = tuple(args.chains or DEFAULT_CHAIN_PATHS)
    while True:
        payload = collect_diagnostics(
            chain_paths,
            burn_fractions=args.burn_fractions,
            primary_burn=args.primary_burn,
        )
        _emit(payload, args.output_dir)
        if not args.watch:
            return 0
        time.sleep(args.interval_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
