#!/usr/bin/env python3
"""Run or safely resume the frozen 12-run WP4 F1 PolyChord campaign."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "runs/prd_extension/wp4_full_cmb/f1_nested"
PRINT_LOCK = threading.Lock()


class F1NestedRunError(RuntimeError):
    """Raised when the nested campaign cannot follow its frozen plan."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _atomic_json(path: Path, payload: dict) -> None:
    import tempfile
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(payload, handle, indent=2, sort_keys=True); handle.write("\n")
        handle.flush(); os.fsync(handle.fileno()); temporary = Path(handle.name)
    os.replace(temporary, path)


def _append(path: Path, event: dict) -> None:
    payload = {**event, "timestamp_utc": datetime.now(timezone.utc).isoformat()}
    with PRINT_LOCK:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
        try: os.write(descriptor, (json.dumps(payload, sort_keys=True) + "\n").encode()); os.fsync(descriptor)
        finally: os.close(descriptor)
        print(json.dumps(payload, sort_keys=True), flush=True)


def validate(output: Path) -> tuple[dict, dict]:
    plan_path = output / "run_plan.json"; activation_path = output / "activation.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    activation = json.loads(activation_path.read_text(encoding="utf-8"))
    if plan.get("status") != "FROZEN_BEFORE_NESTED_PRODUCTION" or activation.get("status") != "ACTIVE_BEFORE_NESTED_PRODUCTION":
        raise F1NestedRunError("nested plan/activation is not authoritative")
    if sha256_file(plan_path) != activation["plan_sha256"]:
        raise F1NestedRunError("nested run-plan hash mismatch")
    start_path = output / "NESTED_PRODUCTION_STARTED.json"
    if not start_path.is_file() or not json.loads(start_path.read_text()).get("production_authorized"):
        raise F1NestedRunError("nested production has not passed its preflight authorization")
    for record in plan["runs"]:
        path = ROOT / record["config"]
        if sha256_file(path) != record["config_sha256"]:
            raise F1NestedRunError(f"nested config hash mismatch: {path}")
    runtime = activation.get("runtime_hashes", {})
    for name, record in runtime.items():
        path = ROOT / record["path"]
        if sha256_file(path) != record["sha256"]:
            raise F1NestedRunError(f"nested runtime hash mismatch: {name}")
    return plan, activation


def _resume_exists(prefix: Path) -> bool:
    return any(prefix.parent.glob(f"{prefix.name}*.resume")) or any(
        prefix.parent.glob(f"{prefix.name}_polychord_raw/*.resume"))


def _run_one(record: dict, events: Path) -> dict:
    config = ROOT / record["config"]; prefix = ROOT / record["output"]
    log = prefix.parent / "nested.log"; evidence = prefix.with_suffix(".evidence.yaml")
    command = ["mpirun", "-np", "4", str(ROOT / ".venv/bin/cobaya-run"), str(config)]
    resume = _resume_exists(prefix)
    if resume: command.append("--resume")
    env = os.environ.copy()
    env.update({name: "1" for name in (
        "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")})
    env["PYTHONPATH"] = str(ROOT)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    _append(events, {"event": "run_start", "seed": record["seed"], "model": record["model"],
                     "resume": resume, "mpi_ranks": 4})
    with log.open("a", encoding="utf-8") as stream:
        result = subprocess.run(command, cwd=ROOT, env=env, stdout=stream,
                                stderr=subprocess.STDOUT, check=False)
    payload = {"seed": record["seed"], "model": record["model"],
               "returncode": result.returncode, "evidence_present": evidence.is_file(),
               "evidence": str(evidence.relative_to(ROOT)),
               "evidence_sha256": sha256_file(evidence) if evidence.is_file() else None,
               "log": str(log.relative_to(ROOT)), "log_sha256": sha256_file(log)}
    _append(events, {"event": "run_exit", **payload})
    return payload


def run(output: Path) -> dict:
    plan, _ = validate(output)
    lock_path = output / "driver.lock"; events = output / "driver_events.jsonl"
    completion_path = output / "completion.json"
    with lock_path.open("w", encoding="utf-8") as lock:
        try: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc: raise F1NestedRunError("another nested driver holds the lock") from exc
        lock.write(str(os.getpid()) + "\n"); lock.flush()
        completion = json.loads(completion_path.read_text()) if completion_path.exists() else {
            "schema_version": "wp4-f1-polychord-completion-v1", "status": "RUNNING", "runs": {}}
        records = {(row["seed"], row["model"]): row for row in plan["runs"]}
        schedule = [((seed, "cpl"), (seed, "lcdm")) for seed in plan["seeds"]] + [
            ((seed, "rip"), (seed, "decay")) for seed in plan["seeds"]]
        _append(events, {"event": "driver_start", "pid": os.getpid(), "remaining": 12-len(completion["runs"])})
        for pair in schedule:
            todo = [records[key] for key in pair if f"{key[0]}_{key[1]}" not in completion["runs"]]
            if not todo: continue
            with ThreadPoolExecutor(max_workers=len(todo)) as executor:
                futures = [executor.submit(_run_one, record, events) for record in todo]
                results = [future.result() for future in futures]
            for result in results:
                key = f"{result['seed']}_{result['model']}"
                if result["returncode"] == 0 and result["evidence_present"]:
                    completion["runs"][key] = result
                else:
                    completion.setdefault("failed_attempts", []).append(result)
            attempts_passed = all(result["returncode"] == 0 and result["evidence_present"]
                                  for result in results)
            passed_so_far = all(row["returncode"] == 0 and row["evidence_present"]
                                for row in completion["runs"].values())
            completion.update(status="RUNNING" if len(completion["runs"]) < 12 else
                              "PASS" if passed_so_far else "FAIL",
                              updated_at_utc=datetime.now(timezone.utc).isoformat(),
                              completed_runs=len(completion["runs"]), total_runs=12)
            _atomic_json(completion_path, completion)
            if not attempts_passed or not passed_so_far:
                raise F1NestedRunError("a PolyChord run failed; inspect its private log and resume unchanged")
        _append(events, {"event": "driver_exit", "status": completion["status"]})
        if completion["status"] == "PASS":
            from pipeline.report_wp4_f1_nested import report
            endpoint = output / "nested_endpoints.json"
            report(output, endpoint, jobs=6)
            _append(events, {"event": "nested_endpoints_written", "path": str(endpoint.relative_to(ROOT)),
                             "sha256": sha256_file(endpoint)})
        return completion


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(); result = run(args.output_root.resolve())
    print(json.dumps({"status": result["status"], "completed_runs": result["completed_runs"]}))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__": raise SystemExit(main())
