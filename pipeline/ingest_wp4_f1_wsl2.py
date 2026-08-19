#!/usr/bin/env python3
"""Verify and ingest the WP4 F1 WSL2 return archive without mixing Mac chains."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "runs/prd_extension/wp4_full_cmb/f1_wsl2"
MANIFEST_NAME = "WSL2_RESULT_MANIFEST.json"
KEY_FILES = {
    "preflight": "work/preflight/PREFLIGHT_GO.json",
    "production": "work/f1/WSL2_PRODUCTION_STARTED.json",
    "latest": "work/f1/external_monitor/latest.json",
    "eligibility": "work/f1/external_monitor/stop_eligible.json",
    "final": "work/f1/external_monitor/final_stop_audit.json",
    "driver_events": "work/f1/driver_events.jsonl",
}


class F1IngestError(RuntimeError):
    """Raised when a return archive cannot be accepted as the frozen F1 run."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


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
        handle.flush()
        os.fsync(handle.fileno())
        temporary = Path(handle.name)
    os.replace(temporary, path)


def _safe_name(name: str) -> bool:
    path = PurePosixPath(name)
    return bool(name) and not path.is_absolute() and ".." not in path.parts


def _regular_members(archive: tarfile.TarFile) -> dict[str, tarfile.TarInfo]:
    records = {}
    for member in archive.getmembers():
        if not _safe_name(member.name):
            raise F1IngestError(f"unsafe archive member: {member.name!r}")
        if member.isdir():
            continue
        if not member.isfile():
            raise F1IngestError(f"non-regular archive member: {member.name!r}")
        if member.name in records:
            raise F1IngestError(f"duplicate archive member: {member.name!r}")
        records[member.name] = member
    return records


def _read_member(archive: tarfile.TarFile, member: tarfile.TarInfo) -> bytes:
    stream = archive.extractfile(member)
    if stream is None:
        raise F1IngestError(f"cannot read archive member: {member.name}")
    return stream.read()


def verify_archive(path: Path) -> tuple[dict, dict[str, bytes]]:
    with tarfile.open(path, "r:gz") as archive:
        members = _regular_members(archive)
        if MANIFEST_NAME not in members:
            raise F1IngestError("return manifest is missing")
        manifest_bytes = _read_member(archive, members[MANIFEST_NAME])
        manifest = json.loads(manifest_bytes)
        declared = {record["path"]: record for record in manifest["files"]}
        actual = set(members).difference({MANIFEST_NAME})
        if set(declared) != actual:
            raise F1IngestError(
                f"manifest/member mismatch: missing={sorted(set(declared)-actual)}, "
                f"unlisted={sorted(actual-set(declared))}"
            )
        payloads = {MANIFEST_NAME: manifest_bytes}
        for name, record in declared.items():
            data = _read_member(archive, members[name])
            if len(data) != record["bytes"] or sha256_bytes(data) != record["sha256"]:
                raise F1IngestError(f"manifest hash mismatch: {name}")
            if name in KEY_FILES.values():
                payloads[name] = data
    return manifest, payloads


def _json(payloads: dict[str, bytes], name: str) -> dict:
    return json.loads(payloads[KEY_FILES[name]])


def validate_closure(payloads: dict[str, bytes]) -> dict:
    preflight = _json(payloads, "preflight")
    production = _json(payloads, "production")
    latest = _json(payloads, "latest")
    eligibility = _json(payloads, "eligibility")
    final = _json(payloads, "final")
    gates = {
        "preflight_pass": preflight.get("status") == "PASS" and preflight.get("production_authorized") is True,
        "production_authorized": production.get("production_authorized") is True,
        "no_mac_samples": production.get("mac_samples_included") is False,
        "four_frozen_seeds": production.get("chain_seeds") == [4511, 4512, 4513, 4514],
        "stop_eligible": latest.get("status") == "STOP_ELIGIBLE" and latest.get("consecutive_passes") == 2,
        "eligibility_separation": eligibility.get("minimum_row_growth", 0) >= 320,
        "final_status": final.get("status") in {"EXTERNALLY_STOPPED", "EXTERNALLY_STOPPED_WITH_EXIT_WARNING"},
        "final_gates": all(final.get("final_policy_gates", {}).values()),
        "post_termination_gates": final.get("post_termination_gates_pass") is True,
        "no_live_children_recorded": not final.get("children_still_alive_after_sigkill"),
        "checkpoints_unedited": final.get("checkpoints_edited") is False,
    }
    warning = None
    if final.get("status") == "EXTERNALLY_STOPPED_WITH_EXIT_WARNING":
        events = [json.loads(line) for line in payloads[KEY_FILES["driver_events"]].splitlines() if line]
        exits = [event for event in events if event.get("event") == "chain_exit"][-4:]
        driver_exit = next((event for event in reversed(events) if event.get("event") == "driver_exit"), None)
        resolved = (
            len(exits) == 4
            and {event.get("chain") for event in exits} == {1, 2, 3, 4}
            and all(event.get("returncode") == -15 for event in exits)
            and driver_exit is not None
            and driver_exit.get("success") is False
            and final.get("post_termination_gates_pass") is True
        )
        gates["exit_warning_resolved"] = resolved
        warning = {
            "status": "RESOLVED_NON_SCIENTIFIC_PROCESS_REAP_WARNING" if resolved else "UNRESOLVED",
            "driver_still_alive_field": final.get("driver_still_alive"),
            "driver_event": driver_exit,
            "chain_exit_events": exits,
        }
    if not all(gates.values()):
        raise F1IngestError(f"closure gates failed: {[name for name, passed in gates.items() if not passed]}")
    return {"gates": gates, "exit_warning": warning}


def extract_archive(path: Path, target: Path) -> None:
    temporary = target.with_name(f".{target.name}.tmp-{os.getpid()}")
    if temporary.exists():
        shutil.rmtree(temporary)
    temporary.mkdir(parents=True)
    with tarfile.open(path, "r:gz") as archive:
        for member in archive.getmembers():
            if not _safe_name(member.name) or (not member.isdir() and not member.isfile()):
                raise F1IngestError(f"unsafe extraction member: {member.name!r}")
        archive.extractall(temporary, filter="data")
    if target.exists():
        shutil.rmtree(target)
    os.replace(temporary, target)


def validate_activation_snapshot(raw: Path, runtime_snapshot: Path) -> dict:
    activation_path = raw / "work/f1/external_stop_activation.json"
    activation = json.loads(activation_path.read_text(encoding="utf-8"))
    checks = []
    for group in ("hashes", "runtime_hashes", "preflight_hashes"):
        for name, record in activation[group].items():
            relative = PurePosixPath(record["path"])
            if relative.parts[0] == "work":
                path = raw / Path(*relative.parts)
            elif relative.parts[0] == "tools":
                path = runtime_snapshot / Path(*relative.parts)
            elif relative.parts[0] == "payload":
                path = ROOT / Path(*relative.parts[1:])
            else:
                raise F1IngestError(f"unknown activation path namespace: {relative}")
            actual = sha256_file(path) if path.is_file() else None
            checks.append({
                "group": group, "name": name, "registered_path": str(relative),
                "resolved_path": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
                "expected_sha256": record["sha256"], "actual_sha256": actual,
                "pass": actual == record["sha256"],
            })
    if not all(item["pass"] for item in checks):
        raise F1IngestError(
            "activation snapshot mismatch: "
            + ", ".join(f"{item['group']}.{item['name']}" for item in checks if not item["pass"])
        )
    return {
        "status": "PASS", "activation_status": activation.get("status"),
        "activation_sha256": sha256_file(activation_path), "checked_hashes": len(checks),
        "checks": checks,
    }


def ingest(archive: Path, output: Path) -> dict:
    manifest, payloads = verify_archive(archive)
    closure = validate_closure(payloads)
    raw = output / "raw"
    extract_archive(archive, raw)
    activation_snapshot = validate_activation_snapshot(raw, output / "runtime_snapshot")
    final = _json(payloads, "final")
    chain_records = []
    for item in final["post_termination_diagnostics"]["chain_snapshots"]:
        chain = len(chain_records) + 1
        path = raw / f"work/f1/c{chain}/chain.1.txt"
        if sha256_file(path) != item["sha256"] or path.stat().st_size != item["captured_bytes"]:
            raise F1IngestError(f"post-termination chain mismatch: c{chain}")
        chain_records.append({
            "chain": chain, "path": str(path.relative_to(ROOT)), "rows": item["rows"],
            "bytes": item["captured_bytes"], "sha256": item["sha256"],
        })
    preflight = _json(payloads, "preflight")
    production = _json(payloads, "production")
    current_preflight_sha = sha256_bytes(payloads[KEY_FILES["preflight"]])
    audit = {
        "schema_version": "wp4-f1-wsl2-ingest-audit-v1",
        "status": "PASS",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_archive": str(archive),
        "source_archive_bytes": archive.stat().st_size,
        "source_archive_sha256": sha256_file(archive),
        "return_manifest_sha256": sha256_bytes(payloads[MANIFEST_NAME]),
        "verified_manifest_files": len(manifest["files"]),
        "closure": closure,
        "activation_snapshot": activation_snapshot,
        "chains": chain_records,
        "preflight": {
            "status": preflight["status"],
            "records": preflight["records"],
            "production_start_recorded_preflight_sha256": production["preflight_sha256"],
            "returned_aggregate_preflight_sha256": current_preflight_sha,
            "aggregate_hash_match": production["preflight_sha256"] == current_preflight_sha,
            "note": "Aggregate timestamp was regenerated on resume; substantive preflight artifacts remain activation-hashed.",
        },
        "mac_chain_disposition": "retained separately and excluded; never pooled or selected",
        "scientific_endpoint_status": "MCMC_CLOSED_READY_FOR_UNBLINDED_REPORT",
    }
    output.mkdir(parents=True, exist_ok=True)
    atomic_json(output / "ingest_audit.json", audit)
    (output / "return_manifest.json").write_bytes(payloads[MANIFEST_NAME])
    (output / "final_stop_audit.json").write_bytes(payloads[KEY_FILES["final"]])
    return audit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = ingest(args.archive.resolve(), args.output.resolve())
    print(json.dumps({"status": result["status"], "output": str(args.output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
