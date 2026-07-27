#!/usr/bin/env python3
"""Run and audit the no-sampling Cobaya initialization test for WP4 F0."""

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
from pathlib import Path

import yaml

from pipeline.wp4_preflight import ROOT, WP4_ROOT, sha256_file


CONFIG = ROOT / "pipeline" / "wp4_f0.yaml"
SMOKE_ROOT = WP4_ROOT / "f0_smoke"
REPORT = WP4_ROOT / "smoke_test.json"
LOG = WP4_ROOT / "smoke_test.log"
INPUT_MANIFEST = WP4_ROOT / "input_manifest.json"

CLIK_CHECK = re.compile(
    r"Checking likelihood '(?P<path>[^']+)' on test data\. got "
    r"(?P<got>[-+0-9.eE]+) expected (?P<expected>[-+0-9.eE]+) "
    r"\(diff (?P<diff>[-+0-9.eE]+)\)"
)

REQUIRED_LOG_MARKERS = (
    "camb` module loaded successfully",
    "[bao.desi_dr2.desi_bao_all] Initialized.",
    "planck_npipe_highl_camspec.ttteee",
    "Loading ACT DR6 lensing likelihood v1.2",
    "Test initialization successful",
)


def parse_clik_checks(text: str) -> list[dict]:
    return [
        {
            "path": match.group("path"),
            "got": float(match.group("got")),
            "expected": float(match.group("expected")),
            "difference": float(match.group("diff")),
        }
        for match in CLIK_CHECK.finditer(text)
    ]


def json_safe(value):
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    return value


def build_report(returncode: int, text: str) -> dict:
    updated = SMOKE_ROOT / "chain.updated.yaml"
    checkpoint = SMOKE_ROOT / "chain.checkpoint"
    chain_files = sorted(SMOKE_ROOT.glob("chain.*.txt"))
    clik_checks = parse_clik_checks(text)
    markers = {marker: marker in text for marker in REQUIRED_LOG_MARKERS}
    checkpoint_payload = (
        yaml.safe_load(checkpoint.read_text(encoding="utf-8"))
        if checkpoint.is_file()
        else None
    )
    passed = (
        returncode == 0
        and all(markers.values())
        and len(clik_checks) == 2
        and updated.is_file()
        and checkpoint.is_file()
        and not chain_files
    )
    return {
        "schema_version": "wp4-f0-smoke-v1",
        "status": "PASS" if passed else "FAIL",
        "command": (
            ".venv/bin/cobaya-run pipeline/wp4_f0.yaml "
            "--test --no-mpi --force"
        ),
        "returncode": returncode,
        "sampling_performed": False,
        "fate_calculation_performed": False,
        "chain_sample_files": [str(path.relative_to(ROOT)) for path in chain_files],
        "config": {
            "path": str(CONFIG.relative_to(ROOT)),
            "sha256": sha256_file(CONFIG),
        },
        "input_manifest": {
            "path": str(INPUT_MANIFEST.relative_to(ROOT)),
            "sha256": sha256_file(INPUT_MANIFEST),
        },
        "updated_config": {
            "path": str(updated.relative_to(ROOT)) if updated.is_file() else None,
            "sha256": sha256_file(updated) if updated.is_file() else None,
        },
        "component_log_markers": markers,
        "clik_self_checks": clik_checks,
        "test_mode_checkpoint": json_safe(checkpoint_payload),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keep-existing", action="store_true")
    args = parser.parse_args(argv)
    if SMOKE_ROOT.exists() and not args.keep_existing:
        shutil.rmtree(SMOKE_ROOT)
    command = [
        str(ROOT / ".venv/bin/cobaya-run"),
        str(CONFIG),
        "--test",
        "--no-mpi",
        "--force",
    ]
    completed = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    WP4_ROOT.mkdir(parents=True, exist_ok=True)
    LOG.write_text(completed.stdout, encoding="utf-8")
    report = build_report(completed.returncode, completed.stdout)
    REPORT.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(completed.stdout, end="")
    print(f"{report['status']}: wrote {REPORT}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
