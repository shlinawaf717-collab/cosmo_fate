#!/usr/bin/env python3
"""Run and audit a no-sampling initialization smoke test for WP4 F1."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import yaml

from pipeline.run_wp4_smoke import CLIK_CHECK, REQUIRED_LOG_MARKERS, json_safe
from pipeline.wp4_preflight import ROOT, WP4_ROOT, sha256_file


CONFIG = ROOT / "pipeline/wp4_f1.yaml"
SMOKE_ROOT = WP4_ROOT / "f1_smoke"
REPORT = WP4_ROOT / "f1_smoke_test.json"
LOG = WP4_ROOT / "f1_smoke_test.log"


def build_report(returncode: int, text: str) -> dict:
    updated = SMOKE_ROOT / "chain.updated.yaml"
    checkpoint = SMOKE_ROOT / "chain.checkpoint"
    chain_files = sorted(SMOKE_ROOT.glob("chain.*.txt"))
    checks = [
        {
            "path": match.group("path"),
            "got": float(match.group("got")),
            "expected": float(match.group("expected")),
            "difference": float(match.group("diff")),
        }
        for match in CLIK_CHECK.finditer(text)
    ]
    markers = {marker: marker in text for marker in REQUIRED_LOG_MARKERS}
    updated_payload = (
        yaml.safe_load(updated.read_text(encoding="utf-8"))
        if updated.is_file() else {}
    )
    f1_markers = {
        # Cobaya's SN class is silent during initialization, so the resolved
        # updated configuration, rather than a non-contractual log line, is
        # the authoritative component check.
        "pantheonplusshoes_in_resolved_config": (
            "sn.pantheonplusshoes" in updated_payload.get("likelihood", {})
            and "sn.pantheonplus" not in updated_payload.get("likelihood", {})
        ),
        "Mb_sampled": "Mb" in text,
        "matter_dom_prior": "matter_dom" in text,
    }
    checkpoint_payload = (
        yaml.safe_load(checkpoint.read_text(encoding="utf-8"))
        if checkpoint.is_file() else None
    )
    passed = (
        returncode == 0 and all(markers.values()) and all(f1_markers.values())
        and len(checks) == 2 and updated.is_file() and checkpoint.is_file()
        and not chain_files
    )
    return {
        "schema_version": "wp4-f1-smoke-v1",
        "status": "PASS" if passed else "FAIL",
        "command": ".venv/bin/cobaya-run pipeline/wp4_f1.yaml --test --no-mpi --force",
        "returncode": returncode,
        "sampling_performed": False,
        "fate_calculation_performed": False,
        "chain_sample_files": [str(path.relative_to(ROOT)) for path in chain_files],
        "config": {"path": str(CONFIG.relative_to(ROOT)), "sha256": sha256_file(CONFIG)},
        "component_log_markers": markers,
        "f1_log_markers": f1_markers,
        "clik_self_checks": checks,
        "test_mode_checkpoint": json_safe(checkpoint_payload),
    }


def main() -> int:
    if SMOKE_ROOT.exists():
        shutil.rmtree(SMOKE_ROOT)
    completed = subprocess.run(
        [str(ROOT / ".venv/bin/cobaya-run"), str(CONFIG), "--test", "--no-mpi", "--force"],
        cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
    )
    LOG.write_text(completed.stdout, encoding="utf-8")
    report = build_report(completed.returncode, completed.stdout)
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(completed.stdout, end="")
    print(f"{report['status']}: wrote {REPORT}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
