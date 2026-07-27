"""Audit the completed 500-noisy-mock WP2 campaign.

The audit is intentionally independent of scientific interpretation.  It
checks campaign completeness, result-ledger consistency, frozen seeds and
inputs, Cobaya convergence gates, and preservation of the migrated v1.x
baseline.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.migrate_null500 import DEFAULT_COVARIANCES, audit_target
from pipeline.run_gate2 import DEFAULT_RUN_ROOT, REQUIRED_MOCK_INPUTS


LABELS = ("CRUNCH", "RIP", "DS", "DECAY", "OTHER")
EXPECTED_INDICES = range(501)
RMINUS1_LIMIT = 0.01
RMINUS1_CL_LIMIT = 0.2
ERROR_LOG_PATTERN = re.compile(
    r"traceback|unhandled exception|segmentation fault|\bkilled\b|\bfatal\b|cobaya exit|error:",
    re.IGNORECASE,
)


class CompletionAuditError(RuntimeError):
    """Raised when the completed campaign fails a frozen audit gate."""


def _finite_number(value, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CompletionAuditError(f"{label} is not numeric: {value!r}")
    number = float(value)
    if not math.isfinite(number):
        raise CompletionAuditError(f"{label} is not finite: {value!r}")
    return number


def _read_ledger(path: Path) -> list[dict]:
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise CompletionAuditError(f"malformed ledger row {line_number}") from exc
        if "error" in row:
            raise CompletionAuditError(f"error record at ledger row {line_number}: {row}")
        rows.append(row)
    indices = [row.get("k") for row in rows]
    if any(isinstance(k, bool) or not isinstance(k, int) for k in indices):
        raise CompletionAuditError("ledger contains a non-integer mock index")
    if len(indices) != len(set(indices)):
        raise CompletionAuditError("ledger contains duplicate mock indices")
    expected = set(EXPECTED_INDICES)
    actual = set(indices)
    if actual != expected:
        raise CompletionAuditError(
            f"ledger index mismatch; missing={sorted(expected - actual)}, "
            f"extra={sorted(actual - expected)}"
        )
    return rows


def _last_progress(path: Path) -> tuple[datetime, datetime, float, float]:
    records = [
        line.split()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]
    if not records:
        raise CompletionAuditError(f"empty progress file: {path}")
    first, last = records[0], records[-1]
    if len(last) != 5:
        raise CompletionAuditError(f"unexpected progress row: {path}: {' '.join(last)}")
    try:
        started = datetime.fromisoformat(first[1])
        finished = datetime.fromisoformat(last[1])
        rminus1 = float(last[3])
        rminus1_cl = float(last[4])
    except (ValueError, IndexError) as exc:
        raise CompletionAuditError(f"invalid progress row: {path}") from exc
    if not math.isfinite(rminus1) or not math.isfinite(rminus1_cl):
        raise CompletionAuditError(f"non-finite final convergence statistic: {path}")
    return started, finished, rminus1, rminus1_cl


def audit_completion(run_root: Path = DEFAULT_RUN_ROOT) -> dict:
    run_root = Path(run_root).resolve()
    mocks_root = run_root / "mocks"
    migration = audit_target(run_root)
    rows = _read_ledger(run_root / "results.jsonl")
    by_k = {row["k"]: row for row in rows}

    max_probability_sum_error = 0.0
    max_heat_identity_error = 0.0
    sample_counts = []
    for k in EXPECTED_INDICES:
        row = by_k[k]
        probabilities = row.get("P")
        errors = row.get("mc_err")
        if not isinstance(probabilities, dict) or set(probabilities) != set(LABELS):
            raise CompletionAuditError(f"mock {k}: invalid probability labels")
        if not isinstance(errors, dict) or set(errors) != set(LABELS):
            raise CompletionAuditError(f"mock {k}: invalid MC-error labels")
        values = [_finite_number(probabilities[label], f"mock {k} P[{label}]") for label in LABELS]
        if any(value < 0 or value > 1 for value in values):
            raise CompletionAuditError(f"mock {k}: probability outside [0, 1]")
        mc_errors = [_finite_number(errors[label], f"mock {k} mc_err[{label}]") for label in LABELS]
        if any(value < 0 for value in mc_errors):
            raise CompletionAuditError(f"mock {k}: negative MC error")
        probability_sum_error = abs(sum(values) - 1.0)
        max_probability_sum_error = max(max_probability_sum_error, probability_sum_error)
        if probability_sum_error > 1e-10:
            raise CompletionAuditError(f"mock {k}: class probabilities do not sum to one")
        heat = _finite_number(row.get("P_heat"), f"mock {k} P_heat")
        heat_error = abs(heat - probabilities["DS"] - probabilities["DECAY"])
        max_heat_identity_error = max(max_heat_identity_error, heat_error)
        if heat_error > 1e-12:
            raise CompletionAuditError(f"mock {k}: P_heat identity mismatch")
        boundary = _finite_number(row.get("boundary_fraction"), f"mock {k} boundary_fraction")
        if boundary < 0 or boundary > 1:
            raise CompletionAuditError(f"mock {k}: boundary fraction outside [0, 1]")
        n_samples = row.get("n_samples")
        if isinstance(n_samples, bool) or not isinstance(n_samples, int) or n_samples <= 0:
            raise CompletionAuditError(f"mock {k}: invalid post-burn-in sample count")
        sample_counts.append(n_samples)

    mock_dirs = {
        path.name for path in mocks_root.iterdir()
        if path.is_dir() and path.name.startswith("m") and path.name[1:].isdigit()
    }
    expected_dirs = {f"m{k:03d}" for k in EXPECTED_INDICES}
    if mock_dirs != expected_dirs:
        raise CompletionAuditError(
            f"mock directory mismatch; missing={sorted(expected_dirs - mock_dirs)}, "
            f"extra={sorted(mock_dirs - expected_dirs)}"
        )

    rminus1_by_k = {}
    rminus1_cl_by_k = {}
    starts = []
    finishes = []
    link_count = 0
    error_log_matches = []
    for k in EXPECTED_INDICES:
        mock_dir = mocks_root / f"m{k:03d}"
        missing = [name for name in REQUIRED_MOCK_INPUTS if not (mock_dir / name).is_file()]
        if missing:
            raise CompletionAuditError(f"mock {k}: missing inputs {missing}")
        for name, canonical in DEFAULT_COVARIANCES.items():
            link = mock_dir / name
            if not link.is_symlink() or Path(os.readlink(link)).is_absolute():
                raise CompletionAuditError(f"mock {k}: non-relative covariance link {name}")
            if link.resolve() != canonical.resolve():
                raise CompletionAuditError(f"mock {k}: covariance link target mismatch {name}")
            link_count += 1

        run_yaml = yaml.safe_load((mock_dir / "run.yaml").read_text(encoding="utf-8"))
        seed = run_yaml.get("sampler", {}).get("mcmc", {}).get("seed")
        if seed != 3000 + k:
            raise CompletionAuditError(f"mock {k}: seed {seed!r} != {3000 + k}")
        chain = mock_dir / "chain.1.txt"
        checkpoint_path = mock_dir / "chain.checkpoint"
        progress = mock_dir / "chain.progress"
        run_log = mock_dir / "run.log"
        for path in (chain, checkpoint_path, progress, run_log):
            if not path.is_file() or path.stat().st_size == 0:
                raise CompletionAuditError(f"mock {k}: missing or empty output {path.name}")
        if ERROR_LOG_PATTERN.search(run_log.read_text(encoding="utf-8", errors="replace")):
            error_log_matches.append(k)
        checkpoint = yaml.safe_load(checkpoint_path.read_text(encoding="utf-8"))
        mcmc = checkpoint.get("sampler", {}).get("mcmc", {})
        if mcmc.get("converged") is not True:
            raise CompletionAuditError(f"mock {k}: checkpoint is not converged")
        checkpoint_rminus1 = _finite_number(mcmc.get("Rminus1_last"), f"mock {k} checkpoint Rminus1")
        started, finished, rminus1, rminus1_cl = _last_progress(progress)
        # The progress table stores six decimal places while the checkpoint
        # retains the full value.
        if abs(checkpoint_rminus1 - rminus1) > 1e-6:
            raise CompletionAuditError(f"mock {k}: checkpoint/progress Rminus1 mismatch")
        if rminus1 >= RMINUS1_LIMIT or rminus1_cl >= RMINUS1_CL_LIMIT:
            raise CompletionAuditError(
                f"mock {k}: convergence gate failed: Rminus1={rminus1}, Rminus1_cl={rminus1_cl}"
            )
        starts.append(started)
        finishes.append(finished)
        rminus1_by_k[k] = rminus1
        rminus1_cl_by_k[k] = rminus1_cl

    if error_log_matches:
        raise CompletionAuditError(
            f"fatal/error signatures found in run logs: {error_log_matches}"
        )

    production_start = min(starts[121:])
    production_finish = max(finishes[121:])
    production_seconds = (production_finish - production_start).total_seconds()
    worst_rminus1_k = max(rminus1_by_k, key=rminus1_by_k.get)
    worst_rminus1_cl_k = max(rminus1_cl_by_k, key=rminus1_cl_by_k.get)
    return {
        "schema_version": "wp2-null500-completion-audit-v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "PASS",
        "campaign": {
            "run_root": str(run_root),
            "mock_indices": [0, 500],
            "noisy_mock_count": 500,
            "result_rows": len(rows),
            "unique_result_indices": len(by_k),
            "mock_directories": len(mock_dirs),
            "chain_files": len(rows),
            "checkpoint_files": len(rows),
            "relative_covariance_links": link_count,
            "seed_rule": "3000 + k",
        },
        "production_m121_m500": {
            "jobs": 6,
            "started_at": production_start.isoformat(),
            "last_chain_converged_at": production_finish.isoformat(),
            "mcmc_span_seconds": production_seconds,
            "throughput_mocks_per_hour": 380 * 3600 / production_seconds,
        },
        "convergence": {
            "passed": len(rows),
            "Rminus1_limit_exclusive": RMINUS1_LIMIT,
            "Rminus1_cl_limit_exclusive": RMINUS1_CL_LIMIT,
            "max_Rminus1": rminus1_by_k[worst_rminus1_k],
            "max_Rminus1_mock": worst_rminus1_k,
            "max_Rminus1_cl": rminus1_cl_by_k[worst_rminus1_cl_k],
            "max_Rminus1_cl_mock": worst_rminus1_cl_k,
        },
        "ledger": {
            "duplicates": 0,
            "missing_indices": [],
            "error_records": 0,
            "fatal_error_log_matches": 0,
            "max_probability_sum_error": max_probability_sum_error,
            "max_P_heat_identity_error": max_heat_identity_error,
            "post_burn_in_samples_min": min(sample_counts),
            "post_burn_in_samples_median": statistics.median(sample_counts),
            "post_burn_in_samples_max": max(sample_counts),
        },
        "migration_audit": migration,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, default=DEFAULT_RUN_ROOT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    report = audit_completion(args.run_root)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
