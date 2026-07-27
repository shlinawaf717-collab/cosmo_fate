"""Apply the frozen WP1 equivalence thresholds to six registered reruns."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import yaml
from getdist import loadMCSamples


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.migrate_null500 import DEFAULT_COVARIANCES
from pipeline.run_gate2 import REQUIRED_MOCK_INPUTS


INDICES = (0, 1, 25, 50, 75, 100)
PARAMETERS = ("ombh2", "omegam", "H0", "w", "wa", "Mb", "omch2", "rdrag")
MEAN_SHIFT_LIMIT = 0.10
FATE_ABSOLUTE_TOLERANCE = 0.02
FATE_MCSE_MULTIPLIER = 3.0
SOURCE_MOCKS = ROOT / "runs" / "gate2" / "mocks"
SOURCE_RESULTS = ROOT / "runs" / "gate2" / "results.jsonl"
DEFAULT_RUN_ROOT = ROOT / "runs" / "prd_extension" / "wp1_equivalence" / "local_m5"


class WP1AuditError(RuntimeError):
    pass


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _ledger(path: Path) -> dict[int, dict]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    by_k = {int(row["k"]): row for row in rows}
    if len(by_k) != len(rows):
        raise WP1AuditError(f"duplicate result index: {path}")
    return by_k


def _chain_summary(root: Path) -> dict[str, dict[str, float]]:
    samples = loadMCSamples(str(root), settings={"ignore_rows": 0.3})
    names = [parameter.name for parameter in samples.paramNames.names]
    means = samples.getMeans()
    covariance = samples.getCov()
    report = {}
    for parameter in PARAMETERS:
        if parameter not in names:
            raise WP1AuditError(f"missing parameter {parameter}: {root}")
        index = names.index(parameter)
        report[parameter] = {
            "mean": float(means[index]),
            "sd": float(math.sqrt(covariance[index, index])),
        }
    return report


def _heat_mc_error(row: dict) -> float:
    return math.hypot(row["mc_err"]["DS"], row["mc_err"]["DECAY"])


def audit_equivalence(
    source_mocks: Path = SOURCE_MOCKS,
    source_results: Path = SOURCE_RESULTS,
    run_root: Path = DEFAULT_RUN_ROOT,
) -> dict:
    source_mocks = Path(source_mocks).resolve()
    run_root = Path(run_root).resolve()
    archived = _ledger(Path(source_results))
    rerun = _ledger(run_root / "results.jsonl")
    if set(rerun) != set(INDICES):
        raise WP1AuditError(
            f"registered rerun result mismatch: expected={list(INDICES)}, actual={sorted(rerun)}"
        )

    cases = {}
    overall_pass = True
    converged_cases = 0
    bitwise_identical_chains = []
    for k in INDICES:
        source_dir = source_mocks / f"m{k:03d}"
        rerun_dir = run_root / "mocks" / f"m{k:03d}"
        if _sha256_file(source_dir / "chain.1.txt") == _sha256_file(
            rerun_dir / "chain.1.txt"
        ):
            bitwise_identical_chains.append(k)
        for name in REQUIRED_MOCK_INPUTS:
            source_input = source_dir / name
            rerun_input = rerun_dir / name
            if name in DEFAULT_COVARIANCES:
                if (
                    not rerun_input.is_symlink()
                    or Path(os.readlink(rerun_input)).is_absolute()
                    or rerun_input.resolve() != DEFAULT_COVARIANCES[name].resolve()
                    or _sha256_file(rerun_input.resolve()) != _sha256_file(source_input.resolve())
                ):
                    raise WP1AuditError(f"mock {k}: covariance input mismatch: {name}")
            elif (
                not rerun_input.is_file()
                or _sha256_file(rerun_input) != _sha256_file(source_input)
            ):
                raise WP1AuditError(f"mock {k}: frozen input mismatch: {name}")

        checkpoint = yaml.safe_load(
            (rerun_dir / "chain.checkpoint").read_text(encoding="utf-8")
        )
        mcmc = checkpoint.get("sampler", {}).get("mcmc", {})
        if mcmc.get("converged") is not True or float(mcmc["Rminus1_last"]) >= 0.01:
            raise WP1AuditError(f"mock {k}: rerun checkpoint failed convergence")
        progress_rows = [
            line.split()
            for line in (rerun_dir / "chain.progress").read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        ]
        if not progress_rows or len(progress_rows[-1]) != 5:
            raise WP1AuditError(f"mock {k}: invalid final progress row")
        final_rminus1 = float(progress_rows[-1][3])
        final_rminus1_cl = float(progress_rows[-1][4])
        if (
            not math.isfinite(final_rminus1)
            or not math.isfinite(final_rminus1_cl)
            or final_rminus1 >= 0.01
            or final_rminus1_cl >= 0.2
        ):
            raise WP1AuditError(f"mock {k}: rerun convergence thresholds failed")
        log_text = (rerun_dir / "run.log").read_text(encoding="utf-8", errors="replace")
        if re.search(
            r"traceback|unhandled exception|segmentation fault|\bkilled\b|\bfatal\b|error:",
            log_text,
            flags=re.IGNORECASE,
        ):
            raise WP1AuditError(f"mock {k}: fatal/error signature in run log")
        converged_cases += 1

        old_summary = _chain_summary(source_dir / "chain")
        new_summary = _chain_summary(rerun_dir / "chain")
        parameter_rows = {}
        for parameter in PARAMETERS:
            old = old_summary[parameter]
            new = new_summary[parameter]
            pooled_sd = math.sqrt((old["sd"] ** 2 + new["sd"] ** 2) / 2)
            standardized_shift = abs(new["mean"] - old["mean"]) / pooled_sd
            passed = standardized_shift <= MEAN_SHIFT_LIMIT
            overall_pass &= passed
            parameter_rows[parameter] = {
                "archived_mean": old["mean"],
                "rerun_mean": new["mean"],
                "archived_sd": old["sd"],
                "rerun_sd": new["sd"],
                "pooled_sd": pooled_sd,
                "absolute_mean_shift": abs(new["mean"] - old["mean"]),
                "shift_in_pooled_sd": standardized_shift,
                "limit": MEAN_SHIFT_LIMIT,
                "pass": passed,
            }

        fate_rows = {}
        for endpoint in ("P_RIP", "P_heat"):
            if endpoint == "P_RIP":
                old_value = archived[k]["P"]["RIP"]
                new_value = rerun[k]["P"]["RIP"]
                old_mcse = archived[k]["mc_err"]["RIP"]
                new_mcse = rerun[k]["mc_err"]["RIP"]
            else:
                old_value = archived[k]["P_heat"]
                new_value = rerun[k]["P_heat"]
                old_mcse = _heat_mc_error(archived[k])
                new_mcse = _heat_mc_error(rerun[k])
            combined_mcse = math.hypot(old_mcse, new_mcse)
            tolerance = max(
                FATE_ABSOLUTE_TOLERANCE,
                FATE_MCSE_MULTIPLIER * combined_mcse,
            )
            difference = abs(new_value - old_value)
            passed = difference <= tolerance
            overall_pass &= passed
            fate_rows[endpoint] = {
                "archived": old_value,
                "rerun": new_value,
                "absolute_difference": difference,
                "archived_mcse": old_mcse,
                "rerun_mcse": new_mcse,
                "combined_mcse": combined_mcse,
                "tolerance": tolerance,
                "pass": passed,
            }
        cases[str(k)] = {"parameters": parameter_rows, "fate": fate_rows}

    worst_parameter = max(
        (
            (row["shift_in_pooled_sd"], int(k), parameter)
            for k, case in cases.items()
            for parameter, row in case["parameters"].items()
        ),
        key=lambda item: item[0],
    )
    return {
        "schema_version": "wp1-equivalence-audit-v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "scope": "local production environment equivalence; x86/Linux cross-platform gate pending",
        "artifact_gates": {
            "frozen_inputs_byte_identical": True,
            "relative_covariance_links_resolve": True,
            "converged_cases": converged_cases,
            "Rminus1_limit_exclusive": 0.01,
            "Rminus1_cl_limit_exclusive": 0.2,
            "fatal_error_log_matches": 0,
            "bitwise_identical_chain_indices": bitwise_identical_chains,
        },
        "registered_indices": list(INDICES),
        "parameter_definition": {
            "parameters": list(PARAMETERS),
            "pooled_sd": "sqrt((sd_archived^2 + sd_rerun^2) / 2)",
            "maximum_shift": MEAN_SHIFT_LIMIT,
        },
        "fate_definition": {
            "endpoints": ["P_RIP", "P_heat"],
            "tolerance": "max(0.02, 3 * hypot(mcse_archived, mcse_rerun))",
        },
        "decision": "PASS_LOCAL_ONLY" if overall_pass else "FAIL",
        "pooling_action": (
            "local old/new pooling equivalence supported; remote x86/Linux WP1 remains pending"
            if overall_pass
            else "do not pool; after the registered diagnostic rerun, rerun all 500 in one locked environment"
        ),
        "worst_parameter_shift": {
            "shift_in_pooled_sd": worst_parameter[0],
            "mock": worst_parameter[1],
            "parameter": worst_parameter[2],
        },
        "cases": cases,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-mocks", type=Path, default=SOURCE_MOCKS)
    parser.add_argument("--source-results", type=Path, default=SOURCE_RESULTS)
    parser.add_argument("--run-root", type=Path, default=DEFAULT_RUN_ROOT)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "runs" / "prd_extension" / "wp1_equivalence" / "local_m5_audit.json",
    )
    args = parser.parse_args(argv)
    report = audit_equivalence(args.source_mocks, args.source_results, args.run_root)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if report["decision"] != "FAIL" else 2


if __name__ == "__main__":
    raise SystemExit(main())
