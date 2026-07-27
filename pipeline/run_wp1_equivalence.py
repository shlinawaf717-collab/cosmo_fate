"""Run the six frozen WP1 equivalence cases in an isolated environment tree.

This runner never writes into ``runs/gate2`` or ``runs/prd_extension/null500``.
It records the active dependency/data/code hashes before launching the same
CPL+P1 MCMC and fate classifier used by WP2.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.migrate_null500 import DEFAULT_COVARIANCES
from pipeline.run_gate2 import (
    REQUIRED_MOCK_INPUTS,
    RunPaths,
    preflight,
    run_one,
)


INDICES = (0, 1, 25, 50, 75, 100)
SOURCE_MOCKS = ROOT / "runs" / "gate2" / "mocks"
DEFAULT_RUN_ROOT = ROOT / "runs" / "prd_extension" / "wp1_equivalence" / "local_m5"
CODE_FILES = (
    "pipeline/run_wp1_equivalence.py",
    "pipeline/run_gate2.py",
    "pipeline/classify_posterior.py",
    "pipeline/fate.py",
    "pipeline/cmb_distprior.py",
    "pipeline/d0_cpl_p1.yaml",
)


class WP1RunError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _command_output(args: list[str]) -> str:
    return subprocess.check_output(args, cwd=ROOT, text=True, stderr=subprocess.STDOUT).strip()


def capture_environment(run_root: Path) -> dict:
    lock = ROOT / "requirements.lock"
    lock_lines = {
        line.strip().lower()
        for line in lock.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    }
    freeze_text = _command_output([sys.executable, "-m", "pip", "freeze"])
    freeze_lines = {line.strip().lower() for line in freeze_text.splitlines() if line.strip()}
    if freeze_lines != lock_lines:
        raise WP1RunError(
            "active environment does not exactly match requirements.lock; "
            f"lock_only={sorted(lock_lines - freeze_lines)}, "
            f"environment_only={sorted(freeze_lines - lock_lines)}"
        )
    data_hashes = {
        name: sha256_file(path.resolve()) for name, path in DEFAULT_COVARIANCES.items()
    }
    code_hashes = {
        relative: sha256_file(ROOT / relative)
        for relative in CODE_FILES
        if (ROOT / relative).is_file()
    }
    report = {
        "schema_version": "wp1-environment-lock-v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "scope": "local production environment equivalence; not x86/Linux cross-platform WP1",
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python": platform.python_version(),
            "macos": platform.mac_ver()[0],
        },
        "git": {
            "commit": _command_output(["git", "rev-parse", "HEAD"]),
            "branch": _command_output(["git", "branch", "--show-current"]),
            "worktree_dirty": bool(_command_output(["git", "status", "--porcelain"])),
        },
        "requirements_lock_sha256": sha256_file(lock),
        "pip_freeze_exactly_matches_lock": True,
        "pip_freeze": freeze_text.splitlines(),
        "data_hashes": data_hashes,
        "code_hashes": code_hashes,
        "registered_indices": list(INDICES),
        "mcmc_seed_rule": "3000 + k",
    }
    environment_dir = ROOT / "runs" / "prd_extension" / "environment"
    environment_dir.mkdir(parents=True, exist_ok=True)
    environment_path = environment_dir / "local_m5_wp1.json"
    environment_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (environment_dir / "local_m5_wp1_requirements_freeze.txt").write_text(
        freeze_text + "\n", encoding="utf-8"
    )
    return report


def stage_inputs(source_mocks: Path, run_root: Path) -> None:
    if run_root.exists():
        manifest_path = run_root / "mocks" / "mocks_manifest.json"
        if not manifest_path.is_file():
            raise WP1RunError(f"refusing unrecognized existing WP1 tree: {run_root}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("schema_version") != "wp1-equivalence-inputs-v1":
            raise WP1RunError(f"unexpected WP1 input schema: {manifest_path}")
        return

    staging = run_root.parent / f".{run_root.name}.staging-{os.getpid()}"
    if staging.exists():
        shutil.rmtree(staging)
    try:
        mocks = staging / "mocks"
        mocks.mkdir(parents=True)
        input_hashes = {}
        for k in INDICES:
            source = source_mocks / f"m{k:03d}"
            target = mocks / f"m{k:03d}"
            target.mkdir()
            input_hashes[str(k)] = {}
            for name in REQUIRED_MOCK_INPUTS:
                source_path = source / name
                target_path = target / name
                if name in DEFAULT_COVARIANCES:
                    canonical = DEFAULT_COVARIANCES[name].resolve()
                    relative = os.path.relpath(canonical, start=target)
                    target_path.symlink_to(relative)
                    input_hashes[str(k)][name] = sha256_file(canonical)
                else:
                    if not source_path.is_file():
                        raise WP1RunError(f"missing frozen input: {source_path}")
                    shutil.copy2(source_path, target_path)
                    input_hashes[str(k)][name] = sha256_file(source_path)
        manifest = {
            "schema_version": "wp1-equivalence-inputs-v1",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source": str(source_mocks.relative_to(ROOT)),
            "indices": list(INDICES),
            "input_hashes": input_hashes,
        }
        (mocks / "mocks_manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        run_root.parent.mkdir(parents=True, exist_ok=True)
        os.replace(staging, run_root)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise


def run_equivalence(
    source_mocks: Path = SOURCE_MOCKS,
    run_root: Path = DEFAULT_RUN_ROOT,
    jobs: int = 6,
) -> dict:
    source_mocks = Path(source_mocks).resolve()
    run_root = Path(run_root).resolve(strict=False)
    try:
        run_root.relative_to((ROOT / "runs" / "prd_extension" / "wp1_equivalence").resolve())
    except ValueError as exc:
        raise WP1RunError(f"WP1 target escapes isolated tree: {run_root}") from exc
    if jobs < 1:
        raise WP1RunError("jobs must be positive")

    environment = capture_environment(run_root)
    stage_inputs(source_mocks, run_root)
    paths = RunPaths.from_root(run_root)
    from pipeline.run_gate2 import done_ks

    completed = done_ks(paths.results)
    indices = [k for k in INDICES if k not in completed]
    preflight(paths, indices)
    started = datetime.now(timezone.utc)
    records = []
    with ThreadPoolExecutor(max_workers=jobs) as executor:
        for record in executor.map(lambda k: run_one(k, paths), indices):
            records.append(record)
            print(
                f"WP1 mock {record['k']:03d}: "
                + (record.get("error") or f"P_heat={record['P_heat']:.6f}"),
                flush=True,
            )
    errors = [record for record in records if "error" in record]
    if errors:
        raise WP1RunError(f"WP1 rerun errors: {errors}")
    report = {
        "schema_version": "wp1-local-rerun-v1",
        "started_at": started.isoformat(),
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "run_root": str(run_root.relative_to(ROOT)),
        "indices": list(INDICES),
        "newly_run": indices,
        "jobs": jobs,
        "environment_lock": "runs/prd_extension/environment/local_m5_wp1.json",
        "environment_scope": environment["scope"],
    }
    (run_root / "rerun_manifest.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-mocks", type=Path, default=SOURCE_MOCKS)
    parser.add_argument("--run-root", type=Path, default=DEFAULT_RUN_ROOT)
    parser.add_argument("--jobs", type=int, default=6)
    args = parser.parse_args(argv)
    report = run_equivalence(args.source_mocks, args.run_root, args.jobs)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
