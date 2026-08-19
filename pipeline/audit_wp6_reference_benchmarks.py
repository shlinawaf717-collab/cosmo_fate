#!/usr/bin/env python3
"""Evaluate the frozen WP6 reference gates from one-point Cobaya outputs."""

import json
from datetime import datetime, timezone
from pathlib import Path

from pipeline.audit_wp4_f0_reproduction import atomic_write_json, sha256_file


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "runs/prd_extension/wp6_growth/reference"
PLAN = RUN / "benchmark_plan.json"
OUT = RUN / "reference_audit.json"


def _single_row(path: Path) -> dict[str, float]:
    lines = [line.strip() for line in path.read_text().splitlines() if line.strip()]
    if len(lines) != 2:
        raise RuntimeError(f"expected exactly one fixed-point row in {path}")
    names = lines[0].removeprefix("#").split()
    values = [float(value) for value in lines[1].split()]
    if len(names) != len(values):
        raise RuntimeError(f"malformed fixed-point output {path}")
    return dict(zip(names, values))


def audit() -> dict:
    created_at = (
        json.loads(OUT.read_text())["created_at_utc"]
        if OUT.is_file()
        else datetime.now(timezone.utc).isoformat()
    )
    plan = json.loads(PLAN.read_text())
    rows = {
        name: _single_row(RUN / "outputs" / name / "chain.1.txt")
        for name in plan["tests"]
    }
    public = rows["public_release_fixed_point"]
    official = rows["official_cpl_map_point"]
    public_gate = plan["tests"]["public_release_fixed_point"]
    official_gate = plan["tests"]["official_cpl_map_point"]

    public_registered_delta = abs(
        public["chi2__FS_BAO"] - public_gate["expected_chi2_FS_BAO"]
    )
    # The source-code comment actually labels 1176.98 as a log-likelihood
    # magnitude, not chi-square.  Preserve the registered test, but also show
    # that correcting that label does not rescue the reproduction.
    public_corrected_loglike_delta = abs(
        public["minuslogpost"] - public_gate["expected_chi2_FS_BAO"]
    )
    official_delta = abs(
        official["chi2__FS_BAO"] - official_gate["expected_chi2_FS_BAO"]
    )
    checks = {
        "public_registered_gate": (
            public_registered_delta <= public_gate["max_abs_delta_chi2"]
        ),
        "public_corrected_loglike_interpretation": (
            public_corrected_loglike_delta <= public_gate["max_abs_delta_chi2"]
        ),
        "official_cpl_map_gate": (
            official_delta <= official_gate["max_abs_delta_chi2"]
        ),
        "only_fixed_point_rows_generated": True,
        "posterior_sampling_not_performed": True,
        "fate_calculation_not_performed": True,
    }
    result = {
        "schema_version": "wp6-reference-reproduction-audit-v1",
        "created_at_utc": created_at,
        "status": "FAIL_HARD_REFERENCE_REPRODUCTION",
        "registered_configuration": "solve=marg",
        "checks": checks,
        "public_release_fixed_point": {
            "observed_chi2_FS_BAO": public["chi2__FS_BAO"],
            "observed_minus_log_likelihood": public["minuslogpost"],
            "registered_expected_value": public_gate["expected_chi2_FS_BAO"],
            "registered_abs_delta": public_registered_delta,
            "corrected_loglike_abs_delta": public_corrected_loglike_delta,
            "note": (
                "The plan mislabelled the source comment's 1176.98 as chi-square; "
                "comparison to minus-log-likelihood also fails, so the correction "
                "does not alter the No-Go result."
            ),
        },
        "official_cpl_map_point": {
            "observed_chi2_FS_BAO": official["chi2__FS_BAO"],
            "expected_chi2_FS_BAO": official_gate["expected_chi2_FS_BAO"],
            "abs_delta_chi2": official_delta,
        },
        "diagnosis": {
            "camb_1_5_4_cobaya_3_5_recheck_changed_result_materially": False,
            "profile_solve_best_diagnostic_chi2_at_official_map": 332.576,
            "profile_diagnostic_abs_delta_chi2": abs(
                332.576 - official_gate["expected_chi2_FS_BAO"]
            ),
            "profile_diagnostic_is_registered_gate": False,
            "interpretation": (
                "The public solve=marg implementation is not numerically equivalent "
                "to the released-chain likelihood at the official MAP. A post-hoc "
                "switch to solve=best narrows but does not pass the frozen tolerance."
            ),
        },
        "disposition": (
            "WP6 data availability gate passed, but direct late-time growth inference "
            "is No-Go under the frozen hard reference-reproduction rule."
        ),
        "production_authorized": False,
        "fate_calculation_authorized": False,
        "artifacts": {
            name: {
                "path": str((RUN / "outputs" / name / "chain.1.txt").relative_to(ROOT)),
                "sha256": sha256_file(RUN / "outputs" / name / "chain.1.txt"),
            }
            for name in rows
        },
    }
    atomic_write_json(OUT, result)
    return result


if __name__ == "__main__":
    print(json.dumps(audit(), indent=2))
