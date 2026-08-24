#!/usr/bin/env python3
"""Authorize WP8 only after source, methods, and synthetic tests are frozen."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from pipeline.audit_wp4_f0_reproduction import atomic_write_json
from pipeline.build_wp7_configs import ROOT
from pipeline.report_wp8 import (
    AUDIT,
    AUTHORIZATION,
    ENDPOINTS,
    EXECUTION,
    PRIMARY_FINAL_AUDIT,
    RESULT_ROOT,
    SOURCE_INVENTORY,
    SOURCE_LEDGER,
    WP7_AUDIT,
    WP7_AUTHORIZATION,
    WP7_ENDPOINTS,
    WP8_V1,
    WP8_V2,
    sha256_file,
)


REPORTER = ROOT / "pipeline/report_wp8.py"
GEOMETRY = ROOT / "pipeline/wp8_future_continuation.py"
REPORTER_TEST = ROOT / "pipeline/test_report_wp8.py"
GEOMETRY_TEST = ROOT / "pipeline/test_wp8_future_continuation.py"
AUTHORIZER_TEST = ROOT / "pipeline/test_authorize_wp8.py"
EXECUTION_MD = ROOT / "plan/WP8_EXECUTION_PROTOCOL.md"


class WP8AuthorizationError(RuntimeError):
    """Raised when the WP8 pre-endpoint transaction is not safe."""


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _chain_identity(record: dict) -> dict:
    path = ROOT / record["path"]
    captured = int(record["captured_bytes"])
    if not path.is_file() or path.stat().st_size < captured:
        raise WP8AuthorizationError(f"WP7 source chain missing or truncated: {path}")
    with path.open("rb") as handle:
        prefix = handle.read(captured)
    rows = sum(1 for line in prefix.splitlines() if line.strip() and not line.startswith(b"#"))
    identity = {
        "path": record["path"],
        "captured_bytes": captured,
        "rows": rows,
        "sha256": hashlib.sha256(prefix).hexdigest(),
        "post_audit_complete_rows_excluded": int(record["post_audit_complete_rows_excluded"]),
    }
    if not prefix.endswith(b"\n"):
        raise WP8AuthorizationError(f"WP7 source prefix lacks a newline boundary: {path}")
    for key in ("captured_bytes", "rows", "sha256"):
        if identity[key] != record[key]:
            raise WP8AuthorizationError(f"WP7 source chain {key} mismatch: {path}")
    return identity


def _live_wp8_processes() -> list[str]:
    output = subprocess.run(
        ["ps", "-axo", "command="], capture_output=True, text=True, check=True
    ).stdout
    return [line.strip() for line in output.splitlines() if "report_wp8.py" in line]


def build_authorization() -> dict:
    required = (
        WP8_V1,
        WP8_V2,
        EXECUTION,
        EXECUTION_MD,
        REPORTER,
        GEOMETRY,
        REPORTER_TEST,
        GEOMETRY_TEST,
        AUTHORIZER_TEST,
        WP7_ENDPOINTS,
        WP7_AUDIT,
        WP7_AUTHORIZATION,
        PRIMARY_FINAL_AUDIT,
    )
    for path in required:
        if not path.is_file():
            raise WP8AuthorizationError(f"required frozen file missing: {path}")
    outputs = (AUTHORIZATION, SOURCE_LEDGER, SOURCE_INVENTORY, ENDPOINTS, AUDIT)
    if any(path.exists() for path in outputs):
        raise WP8AuthorizationError("WP8 authorization or release artifact already exists")

    v1, v2, execution = _load(WP8_V1), _load(WP8_V2), _load(EXECUTION)
    if v1.get("status") != "prospectively frozen before any WP8 result":
        raise WP8AuthorizationError("WP8 v1 protocol is not frozen")
    if v2.get("status") != "frozen before WP8 result":
        raise WP8AuthorizationError("WP8 v2 correction is not frozen")
    if execution.get("status") != "frozen after WP7 closure and before any WP8 endpoint":
        raise WP8AuthorizationError("WP8 execution protocol is not frozen")

    frozen_source_hashes = {
        "wp7_endpoints_sha256": sha256_file(WP7_ENDPOINTS),
        "wp7_postprocessing_audit_sha256": sha256_file(WP7_AUDIT),
        "wp7_authorization_sha256": sha256_file(WP7_AUTHORIZATION),
        "wp7_primary_final_stop_audit_sha256": sha256_file(PRIMARY_FINAL_AUDIT),
    }
    for key, value in frozen_source_hashes.items():
        if execution["source"].get(key) != value:
            raise WP8AuthorizationError(f"WP8 frozen source identity mismatch: {key}")

    wp7_endpoint, wp7_audit = _load(WP7_ENDPOINTS), _load(WP7_AUDIT)
    if wp7_endpoint.get("status") != "PASS" or wp7_audit.get("status") != "PASS":
        raise WP8AuthorizationError("WP7 source endpoint/audit is not PASS")
    primary_stop = _load(PRIMARY_FINAL_AUDIT)
    if primary_stop.get("status") != "EXTERNALLY_STOPPED" or not primary_stop.get(
        "post_termination_gates_pass"
    ):
        raise WP8AuthorizationError("WP7 primary source is not converged and closed")
    wp7_authorization = _load(WP7_AUTHORIZATION)
    source_records = wp7_authorization["settings"]["primary"]["chains"]
    if len(source_records) != 4:
        raise WP8AuthorizationError("WP7 primary source does not have four chains")
    chains = [_chain_identity(record) for record in source_records]

    live = _live_wp8_processes()
    if live:
        raise WP8AuthorizationError("a WP8 reporter process is already alive")

    return {
        "schema_version": "wp8-future-continuation-authorization-v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "AUTHORIZED_AFTER_WP7_CLOSED_BEFORE_WP8_ENDPOINTS",
        "scope": "frozen primary compressed-CMB continuation audit only",
        "v1_protocol_sha256": sha256_file(WP8_V1),
        "v2_protocol_sha256": sha256_file(WP8_V2),
        "execution_protocol_sha256": sha256_file(EXECUTION),
        "execution_protocol_md_sha256": sha256_file(EXECUTION_MD),
        "reporter_sha256": sha256_file(REPORTER),
        "geometry_module_sha256": sha256_file(GEOMETRY),
        "reporter_test_sha256": sha256_file(REPORTER_TEST),
        "geometry_test_sha256": sha256_file(GEOMETRY_TEST),
        "authorizer_sha256": sha256_file(Path(__file__).resolve()),
        "authorizer_test_sha256": sha256_file(AUTHORIZER_TEST),
        **frozen_source_hashes,
        "source": {
            "setting": "primary",
            "chains": chains,
            "all_four_audited_prefixes_match": True,
            "post_audit_suffix_rows_excluded": int(
                sum(row["post_audit_complete_rows_excluded"] for row in chains)
            ),
        },
        "wp7_primary_converged_and_closed": True,
        "synthetic_tests_only_before_authorization": True,
        "WP8_endpoint_calculated_before_authorization": False,
        "no_live_WP8_reporter": True,
        "continuation_endpoint_authorized": True,
        "family_model_average_authorized": False,
        "secondary_full_cmb_authorized": False,
    }


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
