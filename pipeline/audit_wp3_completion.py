"""Audit and summarize the completed registered WP3 power campaign.

This audit is intentionally stricter than the result ledger alone.  It checks
all 606 expected cases, sampler seeds, mock inputs, run artifacts, Cobaya
convergence, probability identities, and fatal log signatures before
calculating the frozen WP3 power endpoints.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import yaml
from scipy.stats import binomtest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.fit_wp3_truths import TRUTH_SPECS, sha256_file
from pipeline.make_wp3_mocks import WP3_ROOT as DEFAULT_WP3_ROOT, audit_campaign
from pipeline.run_wp3 import REQUIRED_MOCK_INPUTS


NULL_ROOT = ROOT / "runs" / "prd_extension" / "null500"
LABELS = ("CRUNCH", "RIP", "DS", "DECAY", "OTHER")
RMINUS1_LIMIT = 0.01
RMINUS1_CL_LIMIT = 0.2
ALPHA = 0.05
ERROR_LOG_PATTERN = re.compile(
    r"traceback|unhandled exception|segmentation fault|\bkilled\b|\bfatal\b|"
    r"cobaya exit|error:",
    re.IGNORECASE,
)


class WP3CompletionError(RuntimeError):
    """Raised when a registered WP3 completion gate fails."""


def _finite(value, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise WP3CompletionError(f"{label} is not numeric: {value!r}")
    result = float(value)
    if not math.isfinite(result):
        raise WP3CompletionError(f"{label} is not finite: {value!r}")
    return result


def exact_interval(successes: int, n: int, confidence: float = 0.95) -> list[float]:
    interval = binomtest(successes, n).proportion_ci(
        confidence_level=confidence,
        method="exact",
    )
    return [float(interval.low), float(interval.high)]


def plus_one_upper_tail(null: np.ndarray, observed: float) -> dict:
    """Finite-simulation upper tail used for truth-consistent depth power."""

    count = int(np.sum(null >= observed))
    n = int(null.size)
    p_value = (count + 1.0) / (n + 1.0)
    return {
        "null_count_greater_or_equal": count,
        "null_n": n,
        "p_plus_one": float(p_value),
        "reject_at_alpha_0p05": bool(p_value <= ALPHA),
    }


def _read_jsonl(path: Path, label: str) -> list[dict]:
    if not path.is_file():
        raise WP3CompletionError(f"{label} ledger is missing: {path}")
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise WP3CompletionError(
                f"{label} ledger has malformed row {line_number}"
            ) from exc
        if "error" in row:
            raise WP3CompletionError(
                f"{label} ledger has error row {line_number}: {row}"
            )
        rows.append(row)
    return rows


def _last_progress(path: Path) -> tuple[datetime, datetime, float, float]:
    records = [
        line.split()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]
    if not records:
        raise WP3CompletionError(f"empty progress file: {path}")
    try:
        started = datetime.fromisoformat(records[0][1])
        finished = datetime.fromisoformat(records[-1][1])
        rminus1 = float(records[-1][3])
        rminus1_cl = float(records[-1][4])
    except (ValueError, IndexError) as exc:
        raise WP3CompletionError(f"invalid final progress row: {path}") from exc
    if not math.isfinite(rminus1) or not math.isfinite(rminus1_cl):
        raise WP3CompletionError(f"non-finite final convergence statistic: {path}")
    return started, finished, rminus1, rminus1_cl


def _correct_mass(row: dict, wa: float) -> float:
    return float(row["P_heat"] if wa < 0 else row["P"]["RIP"])


def _wrong_mass(row: dict, wa: float) -> float:
    return float(row["P"]["RIP"] if wa < 0 else row["P_heat"])


def _rate(successes: int, n: int) -> dict:
    return {
        "successes": int(successes),
        "n": int(n),
        "rate": float(successes / n),
        "exact_binomial_95_interval": exact_interval(successes, n),
    }


def _quantiles(values: np.ndarray) -> dict:
    return {
        "median": float(np.median(values)),
        "central_68_interval": [
            float(np.quantile(values, 0.16)),
            float(np.quantile(values, 0.84)),
        ],
    }


def _validate_probability_row(row: dict, truth_id: str, k: int) -> None:
    prefix = f"{truth_id} m{k:03d}"
    probabilities = row.get("P")
    errors = row.get("mc_err")
    if not isinstance(probabilities, dict) or set(probabilities) != set(LABELS):
        raise WP3CompletionError(f"{prefix}: invalid probability labels")
    if not isinstance(errors, dict) or set(errors) != set(LABELS):
        raise WP3CompletionError(f"{prefix}: invalid MC-error labels")
    p_values = [_finite(probabilities[name], f"{prefix} P[{name}]") for name in LABELS]
    if any(value < 0 or value > 1 for value in p_values):
        raise WP3CompletionError(f"{prefix}: probability outside [0,1]")
    if abs(sum(p_values) - 1.0) > 1e-10:
        raise WP3CompletionError(f"{prefix}: probabilities do not sum to one")
    mc_values = [_finite(errors[name], f"{prefix} mc_err[{name}]") for name in LABELS]
    if any(value < 0 for value in mc_values):
        raise WP3CompletionError(f"{prefix}: negative MC error")
    heat = _finite(row.get("P_heat"), f"{prefix} P_heat")
    if abs(heat - probabilities["DS"] - probabilities["DECAY"]) > 1e-12:
        raise WP3CompletionError(f"{prefix}: P_heat identity mismatch")
    boundary = _finite(row.get("boundary_fraction"), f"{prefix} boundary_fraction")
    if boundary < 0 or boundary > 1:
        raise WP3CompletionError(f"{prefix}: boundary fraction outside [0,1]")
    n_samples = row.get("n_samples")
    if isinstance(n_samples, bool) or not isinstance(n_samples, int) or n_samples <= 0:
        raise WP3CompletionError(f"{prefix}: invalid sample count")


def _load_null(null_root: Path) -> tuple[np.ndarray, np.ndarray]:
    rows = _read_jsonl(null_root / "results.jsonl", "WP2")
    noisy = [row for row in rows if row.get("k") != 0]
    indices = [row.get("k") for row in noisy]
    if len(noisy) != 500 or set(indices) != set(range(1, 501)):
        raise WP3CompletionError("WP2 null ledger is not the frozen 500-noisy campaign")
    if len(indices) != len(set(indices)):
        raise WP3CompletionError("WP2 null ledger contains duplicate indices")
    heat = np.asarray([row["P_heat"] for row in noisy], dtype=float)
    rip = np.asarray([row["P"]["RIP"] for row in noisy], dtype=float)
    if not np.all(np.isfinite(heat)) or not np.all(np.isfinite(rip)):
        raise WP3CompletionError("WP2 null endpoint contains non-finite values")
    return heat, rip


def _monotonicity(points: dict[str, dict]) -> dict:
    """Flag only reversals whose exact 95% intervals are disjoint."""

    sides = {
        "negative_wa": ("wam015", "wam030", "wam060"),
        "positive_wa": ("wap015", "wap030", "wap060"),
    }
    report = {}
    all_clear = True
    for side, truth_ids in sides.items():
        comparisons = []
        for inner, outer in zip(truth_ids, truth_ids[1:]):
            inner_rate = points[inner]["direction_power"]
            outer_rate = points[outer]["direction_power"]
            reversal = outer_rate["rate"] < inner_rate["rate"]
            beyond = (
                reversal
                and outer_rate["exact_binomial_95_interval"][1]
                < inner_rate["exact_binomial_95_interval"][0]
            )
            all_clear &= not beyond
            comparisons.append(
                {
                    "inner_truth": inner,
                    "outer_truth": outer,
                    "point_estimate_reversal": reversal,
                    "reversal_beyond_binomial_uncertainty": beyond,
                }
            )
        report[side] = comparisons
    report["status"] = "PASS" if all_clear else "DIAGNOSTIC_TRIGGERED"
    report["definition"] = (
        "A reversal is beyond binomial uncertainty only when the outer point "
        "estimate is lower and its exact 95% upper bound is below the inner "
        "point's exact 95% lower bound."
    )
    return report


def audit_completion(
    wp3_root: Path = DEFAULT_WP3_ROOT,
    null_root: Path = NULL_ROOT,
) -> dict:
    wp3_root = Path(wp3_root).resolve()
    null_root = Path(null_root).resolve()
    if wp3_root != DEFAULT_WP3_ROOT.resolve():
        raise WP3CompletionError(
            "custom WP3 roots are unsupported because the frozen input audit "
            "is content-addressed to the registered campaign"
        )
    input_audit = audit_campaign()
    rows = _read_jsonl(wp3_root / "results.jsonl", "WP3")
    if len(rows) != 606:
        raise WP3CompletionError(f"WP3 ledger has {len(rows)} rows, expected 606")
    pairs = [(str(row.get("truth_id")), row.get("k")) for row in rows]
    if len(pairs) != len(set(pairs)):
        raise WP3CompletionError("WP3 ledger contains duplicate (truth_id,k) pairs")

    expected = {
        (truth_id, k)
        for truth_id, _, _, _ in TRUTH_SPECS
        for k in range(101)
    }
    if set(pairs) != expected:
        raise WP3CompletionError(
            f"WP3 ledger pair mismatch; missing={sorted(expected - set(pairs))}, "
            f"extra={sorted(set(pairs) - expected)}"
        )
    by_pair = {(str(row["truth_id"]), int(row["k"])): row for row in rows}

    null_heat, null_rip = _load_null(null_root)
    starts = []
    finishes = []
    rminus1_values = {}
    rminus1_cl_values = {}
    sample_counts = []
    max_probability_sum_error = 0.0
    max_heat_identity_error = 0.0
    fatal_logs = []
    truth_points = {}

    for ordinal, (truth_id, wa, _, _) in enumerate(TRUTH_SPECS, start=1):
        truth_rows = []
        for k in range(101):
            row = by_pair[(truth_id, k)]
            expected_seed = 310000 + 1000 * ordinal + k
            expected_kind = "asimov" if k == 0 else "noisy"
            if row.get("truth_ordinal") != ordinal:
                raise WP3CompletionError(f"{truth_id} m{k:03d}: truth ordinal mismatch")
            if float(row.get("wa_truth")) != wa:
                raise WP3CompletionError(f"{truth_id} m{k:03d}: wa truth mismatch")
            if row.get("seed") != expected_seed:
                raise WP3CompletionError(f"{truth_id} m{k:03d}: ledger seed mismatch")
            if row.get("kind") != expected_kind:
                raise WP3CompletionError(f"{truth_id} m{k:03d}: kind mismatch")
            _validate_probability_row(row, truth_id, k)
            values = [float(row["P"][name]) for name in LABELS]
            max_probability_sum_error = max(
                max_probability_sum_error,
                abs(sum(values) - 1.0),
            )
            max_heat_identity_error = max(
                max_heat_identity_error,
                abs(float(row["P_heat"]) - row["P"]["DS"] - row["P"]["DECAY"]),
            )
            sample_counts.append(int(row["n_samples"]))

            mock_dir = wp3_root / truth_id / "mocks" / f"m{k:03d}"
            missing_inputs = [
                name for name in REQUIRED_MOCK_INPUTS if not (mock_dir / name).is_file()
            ]
            if missing_inputs:
                raise WP3CompletionError(
                    f"{truth_id} m{k:03d}: missing inputs {missing_inputs}"
                )
            run_yaml_path = mock_dir / "run.yaml"
            chain_path = mock_dir / "chain.1.txt"
            checkpoint_path = mock_dir / "chain.checkpoint"
            progress_path = mock_dir / "chain.progress"
            log_path = mock_dir / "run.log"
            for path in (
                run_yaml_path,
                chain_path,
                checkpoint_path,
                progress_path,
                log_path,
            ):
                if not path.is_file() or path.stat().st_size == 0:
                    raise WP3CompletionError(
                        f"{truth_id} m{k:03d}: missing or empty {path.name}"
                    )
            run_yaml = yaml.safe_load(run_yaml_path.read_text(encoding="utf-8"))
            yaml_seed = run_yaml.get("sampler", {}).get("mcmc", {}).get("seed")
            if yaml_seed != expected_seed:
                raise WP3CompletionError(f"{truth_id} m{k:03d}: YAML seed mismatch")
            checkpoint = yaml.safe_load(checkpoint_path.read_text(encoding="utf-8"))
            mcmc = checkpoint.get("sampler", {}).get("mcmc", {})
            if mcmc.get("converged") is not True:
                raise WP3CompletionError(
                    f"{truth_id} m{k:03d}: unresolved checkpoint"
                )
            checkpoint_r1 = _finite(
                mcmc.get("Rminus1_last"),
                f"{truth_id} m{k:03d} checkpoint Rminus1",
            )
            started, finished, r1, r1_cl = _last_progress(progress_path)
            if abs(checkpoint_r1 - r1) > 1e-6:
                raise WP3CompletionError(
                    f"{truth_id} m{k:03d}: checkpoint/progress Rminus1 mismatch"
                )
            if r1 >= RMINUS1_LIMIT or r1_cl >= RMINUS1_CL_LIMIT:
                raise WP3CompletionError(
                    f"{truth_id} m{k:03d}: convergence gate failed "
                    f"Rminus1={r1}, Rminus1_cl={r1_cl}"
                )
            if ERROR_LOG_PATTERN.search(
                log_path.read_text(encoding="utf-8", errors="replace")
            ):
                fatal_logs.append(f"{truth_id}/m{k:03d}")
            starts.append(started)
            finishes.append(finished)
            rminus1_values[(truth_id, k)] = r1
            rminus1_cl_values[(truth_id, k)] = r1_cl
            if k > 0:
                truth_rows.append(row)

        correct = np.asarray([_correct_mass(row, wa) for row in truth_rows])
        wrong = np.asarray([_wrong_mass(row, wa) for row in truth_rows])
        null_correct = null_heat if wa < 0 else null_rip
        depth_rows = [
            plus_one_upper_tail(null_correct, float(value)) for value in correct
        ]
        direction_successes = int(np.sum(correct > 0.5))
        false_sign_successes = int(np.sum(wrong > 0.5))
        depth_successes = int(
            sum(row["reject_at_alpha_0p05"] for row in depth_rows)
        )
        asimov = by_pair[(truth_id, 0)]
        truth_points[truth_id] = {
            "wa": wa,
            "correct_direction": "heat_death_compatible" if wa < 0 else "RIP",
            "correct_mass_definition": "P_heat" if wa < 0 else "P_RIP",
            "direction_power": _rate(direction_successes, 100),
            "one_sided_depth_power": _rate(depth_successes, 100),
            "false_sign_fraction": _rate(false_sign_successes, 100),
            "correct_mass_distribution": _quantiles(correct),
            "asimov_correct_mass": _correct_mass(asimov, wa),
            "depth_test": {
                "null_endpoint": "P_heat" if wa < 0 else "P_RIP",
                "null_n": 500,
                "tail": "upper",
                "alpha": ALPHA,
                "finite_simulation_rule": "(1 + count(null >= mock))/(500 + 1) <= 0.05",
                "minimum_p_plus_one": float(
                    min(row["p_plus_one"] for row in depth_rows)
                ),
                "maximum_p_plus_one": float(
                    max(row["p_plus_one"] for row in depth_rows)
                ),
            },
        }

    if fatal_logs:
        raise WP3CompletionError(f"fatal/error log signatures: {fatal_logs}")

    worst_r1 = max(rminus1_values, key=rminus1_values.get)
    worst_r1_cl = max(rminus1_cl_values, key=rminus1_cl_values.get)
    outer_pass = (
        truth_points["wam060"]["direction_power"]["rate"] >= 0.80
        and truth_points["wap060"]["direction_power"]["rate"] >= 0.80
    )
    monotonicity = _monotonicity(truth_points)
    return {
        "schema_version": "wp3-power-completion-audit-v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "PASS",
        "campaign": {
            "run_root": str(wp3_root),
            "truth_points": 6,
            "asimov_cases": 6,
            "noisy_cases": 600,
            "result_rows": len(rows),
            "unique_truth_mock_pairs": len(set(pairs)),
            "duplicate_pairs": 0,
            "error_rows": 0,
            "seed_rule": "310000 + 1000*j + k; k=0 Asimov per PRD-A004",
            "first_final_chain_started_at": min(starts).isoformat(),
            "last_final_chain_converged_at": max(finishes).isoformat(),
        },
        "input_audit": input_audit,
        "artifact_and_convergence_audit": {
            "passed_cases": 606,
            "missing_cases": 0,
            "fatal_error_log_matches": 0,
            "Rminus1_limit_exclusive": RMINUS1_LIMIT,
            "Rminus1_cl_limit_exclusive": RMINUS1_CL_LIMIT,
            "max_Rminus1": rminus1_values[worst_r1],
            "max_Rminus1_case": {"truth_id": worst_r1[0], "k": worst_r1[1]},
            "max_Rminus1_cl": rminus1_cl_values[worst_r1_cl],
            "max_Rminus1_cl_case": {
                "truth_id": worst_r1_cl[0],
                "k": worst_r1_cl[1],
            },
            "post_burn_in_samples_min": min(sample_counts),
            "post_burn_in_samples_median": statistics.median(sample_counts),
            "post_burn_in_samples_max": max(sample_counts),
            "max_probability_sum_error": max_probability_sum_error,
            "max_P_heat_identity_error": max_heat_identity_error,
        },
        "registered_power_endpoints": {
            "alpha": ALPHA,
            "truth_points": truth_points,
            "outer_direction_power_threshold": 0.80,
            "outer_points_pass": outer_pass,
            "classifier_demonstrably_powerful": outer_pass,
            "monotonicity_diagnostic": monotonicity,
        },
        "operational_history": {
            "driver_interruptions": 2,
            "completed_noisy_counts_at_detection": [485, 514],
            "disposition": (
                "No result-ledger, input, resource, or scientific error was found. "
                "The same command, jobs=6, inputs, and deterministic seeds were "
                "used for resume. Incomplete cases were rerun; no completed ledger "
                "pair was duplicated. The final resume ran in detached screen."
            ),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wp3-root", type=Path, default=DEFAULT_WP3_ROOT)
    parser.add_argument("--null-root", type=Path, default=NULL_ROOT)
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_WP3_ROOT / "completion_audit.json",
    )
    args = parser.parse_args(argv)
    report = audit_completion(args.wp3_root, args.null_root)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
