#!/usr/bin/env python3
"""Authorize WP7 endpoint reporting after verifying all blinded closures."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from pipeline.audit_wp4_f0_reproduction import atomic_write_json
from pipeline.build_wp7_configs import ROOT, SETTINGS
from pipeline.report_wp7 import (
    AUDIT,
    AUTHORIZATION,
    AUTHORIZATION_V1,
    ENDPOINTS,
    INFORMATION_PLAN,
    PROTOCOL,
    SBC_REPORT,
    SYSTEM,
    sha256_file,
)


EXECUTION_PROTOCOL = ROOT / "plan/wp7_execution_protocol.json"
PROTOCOL_MD = ROOT / "plan/WP7_POSTPROCESSING_PROTOCOL.md"
REPORTER = ROOT / "pipeline/report_wp7.py"
REPORTER_TEST = ROOT / "pipeline/test_report_wp7.py"
AUTHORIZER_TEST = ROOT / "pipeline/test_authorize_wp7_postprocessing.py"


class WP7AuthorizationError(RuntimeError):
    """Raised when WP7 post-processing is not prospectively safe."""


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _complete_rows(path: Path) -> int:
    with path.open("r", encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip() and not line.startswith("#"))


def chain_identity(path: Path, expected: dict) -> dict:
    path = path.resolve()
    try:
        relative = path.relative_to(ROOT)
    except ValueError as exc:
        raise WP7AuthorizationError(f"chain is outside repository: {path}") from exc
    captured = int(expected["captured_bytes"])
    current_bytes = path.stat().st_size
    if current_bytes < captured:
        raise WP7AuthorizationError(f"chain is shorter than final audit: {path}")
    with path.open("rb") as handle:
        prefix = handle.read(captured)
    if len(prefix) != captured or not prefix.endswith(b"\n"):
        raise WP7AuthorizationError(f"audited prefix is not a complete line boundary: {path}")
    prefix_rows = sum(1 for line in prefix.splitlines() if line.strip() and not line.startswith(b"#"))
    current_rows = _complete_rows(path)
    identity = {
        "path": str(relative),
        "rows": prefix_rows,
        "captured_bytes": captured,
        "sha256": hashlib.sha256(prefix).hexdigest(),
        "current_complete_rows": current_rows,
        "current_bytes": current_bytes,
        "current_full_sha256": sha256_file(path),
        "post_audit_complete_rows_excluded": current_rows - prefix_rows,
        "post_audit_bytes_excluded": current_bytes - captured,
        "total_weight_at_final_stop": int(expected["total_weight"]),
    }
    comparisons = {
        "rows": int(expected["rows"]),
        "captured_bytes": int(expected["captured_bytes"]),
        "sha256": expected["sha256"],
    }
    for key, value in comparisons.items():
        if identity[key] != value:
            raise WP7AuthorizationError(f"chain {key} differs from final audit: {path}")
    return identity


def _setting_identity(tag: str) -> dict:
    audit_path = SYSTEM / tag / "external_monitor/final_stop_audit.json"
    audit = _load(audit_path)
    if audit.get("status") != "EXTERNALLY_STOPPED":
        raise WP7AuthorizationError(f"{tag} is not externally stopped")
    if not audit.get("post_termination_gates_pass"):
        raise WP7AuthorizationError(f"{tag} post-termination gates failed")
    if audit.get("children_still_alive_after_sigkill"):
        raise WP7AuthorizationError(f"{tag} has surviving children")
    diagnostics = audit["post_termination_diagnostics"]
    if not all(diagnostics["candidate_gates"].values()):
        raise WP7AuthorizationError(f"{tag} final candidate gate failed")
    snapshots = diagnostics["chain_snapshots"]
    if len(snapshots) != 4:
        raise WP7AuthorizationError(f"{tag} does not have four final chains")
    chains = [chain_identity(Path(record["path"]), record) for record in snapshots]
    payload = {
        "final_stop_audit": {
            "path": str(audit_path.relative_to(ROOT)),
            "sha256": sha256_file(audit_path),
            "completed_at_utc": audit["completed_at_utc"],
        },
        "chains": chains,
        "all_post_termination_gates_pass": True,
    }


def _live_wp7_samplers() -> list[str]:
    output = subprocess.run(
        ["ps", "-axo", "command="], capture_output=True, text=True, check=True
    ).stdout
    return [
        line.strip()
        for line in output.splitlines()
        if "cobaya-run" in line and "production_system/" in line and "wp7" in line
    ]


def build_authorization() -> dict:
    for path in (PROTOCOL, PROTOCOL_MD, REPORTER, REPORTER_TEST, AUTHORIZER_TEST):
        if not path.is_file():
            raise WP7AuthorizationError(f"required frozen post-processing file missing: {path}")
    if AUTHORIZATION.exists() or ENDPOINTS.exists() or AUDIT.exists():
        raise WP7AuthorizationError("WP7 post-processing or endpoint artifact already exists")
    execution = _load(EXECUTION_PROTOCOL)
    if execution.get("status") != "FROZEN_BEFORE_WP7_POSTERIOR_SAMPLING":
        raise WP7AuthorizationError("WP7 execution protocol is not frozen")
    postprocessing = _load(PROTOCOL)
    if postprocessing.get("status") != "CORRECTED_AND_REFROZEN_BEFORE_ENDPOINT_CALCULATION":
        raise WP7AuthorizationError("WP7 post-processing protocol is not frozen")
    information = _load(INFORMATION_PLAN)
    if information.get("status") != "FROZEN_BEFORE_WP7_POSTERIOR":
        raise WP7AuthorizationError("WP7 information plan is not frozen")
    sbc = _load(SBC_REPORT)
    if sbc.get("status") != "PASS" or not all(sbc.get("gates", {}).values()):
        raise WP7AuthorizationError("WP7 SBC is not a complete PASS")
    live = _live_wp7_samplers()
    if live:
        raise WP7AuthorizationError("WP7 posterior samplers are still alive")
    settings = {tag: _setting_identity(tag) for tag in SETTINGS}
    return {
        "schema_version": "wp7-fs7-postprocessing-authorization-v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "AUTHORIZED_AFTER_ALL_SETTINGS_CLOSED_BEFORE_ENDPOINTS",
        "scope": "technical post-processing choices frozen and tested without reading a real posterior endpoint",
        "postprocessing_protocol_sha256": sha256_file(PROTOCOL),
        "postprocessing_protocol_md_sha256": sha256_file(PROTOCOL_MD),
        "execution_protocol_sha256": sha256_file(EXECUTION_PROTOCOL),
        "information_plan_sha256": sha256_file(INFORMATION_PLAN),
        "sbc_report_sha256": sha256_file(SBC_REPORT),
        "reporter_sha256": sha256_file(REPORTER),
        "reporter_test_sha256": sha256_file(REPORTER_TEST),
        "authorizer_sha256": sha256_file(Path(__file__).resolve()),
        "authorizer_test_sha256": sha256_file(AUTHORIZER_TEST),
        "settings": settings,
        "all_20_audited_chain_prefixes_match_final_stop_audits": True,
        "append_only_suffixes_excluded_from_endpoints": {
            tag: int(sum(row["post_audit_complete_rows_excluded"] for row in record["chains"]))
            for tag, record in settings.items()
        },
        "all_five_settings_closed": True,
        "sbc_pass": True,
        "no_live_wp7_sampler": True,
        "posterior_location_or_endpoint_read_before_authorization": False,
        "synthetic_tests_only_before_authorization": True,
        "fate_calculation_authorized": True,
        "kl_calculation_authorized": True,
        "between_setting_comparison_authorized": True,
        "model_evidence_authorized": False,
    }
    if AUTHORIZATION_V1.is_file():
        payload["supersedes_authorization"] = {
            "path": str(AUTHORIZATION_V1.relative_to(ROOT)),
            "sha256": sha256_file(AUTHORIZATION_V1),
            "reason": "v1 reporter validation used the wrong protocol-hash field name and failed before reading a chain value",
            "v1_endpoint_calculation_started": False,
        }
    return payload


def authorize(output: Path = AUTHORIZATION) -> dict:
    payload = build_authorization()
    atomic_write_json(output, payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=AUTHORIZATION)
    args = parser.parse_args()
    payload = authorize(args.output.resolve())
    print(json.dumps({"status": payload["status"], "output": str(args.output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
