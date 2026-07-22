"""Atomically stage the completed v1.x null mocks for the PRD WP2 campaign.

The migration copies ``m000`` through ``m100`` without modifying the source,
rewrites the two host-absolute covariance links in every mock as relative
repository links, copies the v1.x result ledger and fitted-truth snapshot, and
records a content inventory. The final directory appears only after every
validation passes.

Usage:
  .venv/bin/python pipeline/migrate_null500.py --dry-run
  .venv/bin/python pipeline/migrate_null500.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_MOCKS = ROOT / "runs" / "gate2" / "mocks"
SOURCE_RESULTS = ROOT / "runs" / "gate2" / "results.jsonl"
SOURCE_TRUTH = ROOT / "runs" / "gate2" / "truth_lcdm_d0.json"
TARGET_ROOT = ROOT / "runs" / "prd_extension" / "null500"
PROTOCOL = ROOT / "plan" / "prd_extension_protocol.json"

DEFAULT_COVARIANCES = {
    "sn_cov.cov": (
        ROOT
        / "data"
        / "cobaya_packages"
        / "data"
        / "sn_data"
        / "PantheonPlus"
        / "Pantheon+SH0ES_STAT+SYS.cov"
    ),
    "bao_cov.txt": (
        ROOT
        / "data"
        / "cobaya_packages"
        / "data"
        / "bao_data"
        / "desi_bao_dr2"
        / "desi_gaussian_bao_ALL_GCcomb_cov.txt"
    ),
}

REQUIRED_SOURCE_FILES = (
    "sn_mock.dat",
    "config.dataset",
    "bao_mean.txt",
    "cmb_mean.json",
    "chain.1.txt",
    "chain.input.yaml",
    "chain.updated.yaml",
    "chain.covmat",
)


class MigrationError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(value) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def tree_inventory(root: Path) -> list[dict]:
    entries: list[dict] = []
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            entries.append({"path": relative, "type": "symlink", "target": os.readlink(path)})
        elif path.is_file():
            entries.append(
                {
                    "path": relative,
                    "type": "file",
                    "size": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
            )
    return entries


def regular_tree_digest(inventory: list[dict]) -> str:
    return canonical_sha256([entry for entry in inventory if entry["type"] == "file"])


def read_results(path: Path, expected_noisy: int) -> list[dict]:
    rows: list[dict] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        try:
            row = json.loads(line)
            row["k"] = int(row["k"])
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise MigrationError(f"invalid result at {path}:{line_number}") from exc
        rows.append(row)
    indices = [row["k"] for row in rows]
    expected = set(range(expected_noisy + 1))
    if len(indices) != len(set(indices)):
        raise MigrationError("source result ledger contains duplicate mock indices")
    if set(indices) != expected:
        missing = sorted(expected - set(indices))
        extra = sorted(set(indices) - expected)
        raise MigrationError(f"source result ledger index mismatch; missing={missing}, extra={extra}")
    return rows


def validate_source(
    source_mocks: Path,
    source_results: Path,
    source_truth: Path,
    covariances: dict[str, Path],
    expected_noisy: int,
) -> dict:
    for path in (source_mocks, source_results, source_truth):
        if not path.exists():
            raise MigrationError(f"required source is missing: {path}")
    manifest_path = source_mocks / "mocks_manifest.json"
    if not manifest_path.is_file():
        raise MigrationError(f"source mock manifest is missing: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("seed") != 42 or manifest.get("n") != expected_noisy:
        raise MigrationError(
            f"source mock manifest must declare seed=42 and n={expected_noisy}: {manifest_path}"
        )

    actual_dirs = {
        path.name
        for path in source_mocks.iterdir()
        if path.is_dir() and path.name.startswith("m") and path.name[1:].isdigit()
    }
    expected_dirs = {f"m{k:03d}" for k in range(expected_noisy + 1)}
    if actual_dirs != expected_dirs:
        raise MigrationError(
            f"source mock directory mismatch; missing={sorted(expected_dirs - actual_dirs)}, "
            f"extra={sorted(actual_dirs - expected_dirs)}"
        )

    for k in range(expected_noisy + 1):
        mock_dir = source_mocks / f"m{k:03d}"
        if mock_dir.is_symlink():
            raise MigrationError(f"source mock directory may not be a symlink: {mock_dir}")
        missing = [name for name in REQUIRED_SOURCE_FILES if not (mock_dir / name).is_file()]
        if missing:
            raise MigrationError(f"source mock {mock_dir.name} is incomplete: {missing}")

    for canonical in covariances.values():
        if not canonical.is_file():
            raise MigrationError(f"canonical covariance is missing: {canonical}")
    for name, canonical in covariances.items():
        for k in range(expected_noisy + 1):
            link = source_mocks / f"m{k:03d}" / name
            if not link.is_symlink():
                raise MigrationError(f"expected covariance symlink is missing: {link}")
            if link.resolve() != canonical.resolve():
                raise MigrationError(f"covariance symlink has unexpected target: {link} -> {link.resolve()}")

    rows = read_results(source_results, expected_noisy)
    return {"manifest": manifest, "result_rows": len(rows)}


def git_blob_sha256(commit: str, repo_path: str) -> str:
    try:
        payload = subprocess.check_output(
            ["git", "show", f"{commit}:{repo_path}"], cwd=ROOT, stderr=subprocess.PIPE
        )
    except subprocess.CalledProcessError as exc:
        raise MigrationError(f"cannot read {repo_path} from baseline commit {commit}") from exc
    return hashlib.sha256(payload).hexdigest()


def relative_to_root(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def rewrite_covariance_links(
    target_mocks: Path, covariances: dict[str, Path], expected_noisy: int
) -> dict[str, dict]:
    report: dict[str, dict] = {}
    for name, canonical in covariances.items():
        target_text: str | None = None
        for k in range(expected_noisy + 1):
            link = target_mocks / f"m{k:03d}" / name
            if link.exists() or link.is_symlink():
                link.unlink()
            relative = os.path.relpath(canonical.resolve(), start=link.parent.resolve())
            link.symlink_to(relative)
            if Path(os.readlink(link)).is_absolute() or link.resolve() != canonical.resolve():
                raise MigrationError(f"portable covariance link validation failed: {link}")
            if target_text is None:
                target_text = relative
            elif target_text != relative:
                raise MigrationError(f"inconsistent relative covariance target for {name}")
        report[name] = {
            "mode": "relative-symlink",
            "canonical_source": relative_to_root(canonical),
            "canonical_sha256": sha256_file(canonical),
            "relative_target": target_text,
            "links_rewritten": expected_noisy + 1,
        }
    return report


def verify_baseline_tracked_files(commit: str, source_results: Path, source_truth: Path) -> dict:
    report = {}
    for label, path in (("results", source_results), ("truth", source_truth)):
        repo_path = path.relative_to(ROOT).as_posix()
        worktree_sha = sha256_file(path)
        baseline_sha = git_blob_sha256(commit, repo_path)
        if worktree_sha != baseline_sha:
            raise MigrationError(f"{repo_path} differs from frozen baseline commit {commit}")
        report[label] = {
            "path": repo_path,
            "sha256": worktree_sha,
            "matches_baseline_commit": True,
        }
    return report


def migrate(
    source_mocks: Path = SOURCE_MOCKS,
    source_results: Path = SOURCE_RESULTS,
    source_truth: Path = SOURCE_TRUTH,
    target_root: Path = TARGET_ROOT,
    covariances: dict[str, Path] | None = None,
    expected_noisy: int = 100,
    dry_run: bool = False,
    verify_git: bool = True,
) -> dict:
    source_mocks = Path(source_mocks).resolve()
    source_results = Path(source_results).resolve()
    source_truth = Path(source_truth).resolve()
    target_root = Path(target_root).resolve(strict=False)
    covariances = {
        name: Path(path).resolve() for name, path in (covariances or DEFAULT_COVARIANCES).items()
    }
    if target_root.exists():
        raise MigrationError(f"refusing to overwrite existing target: {target_root}")

    source_summary = validate_source(
        source_mocks, source_results, source_truth, covariances, expected_noisy
    )
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8")) if PROTOCOL.exists() else {}
    baseline = protocol.get("baseline", {})
    baseline_commit = baseline.get("commit")
    baseline_tag = baseline.get("tag")
    git_verification = None
    if verify_git:
        if not baseline_commit:
            raise MigrationError("frozen baseline commit is missing from the PRD protocol")
        git_verification = verify_baseline_tracked_files(
            baseline_commit, source_results, source_truth
        )

    source_inventory_before = tree_inventory(source_mocks)
    source_regular_sha = regular_tree_digest(source_inventory_before)
    plan = {
        "source": relative_to_root(source_mocks),
        "target": relative_to_root(target_root),
        "mock_directories": expected_noisy + 1,
        "result_rows": source_summary["result_rows"],
        "source_regular_tree_sha256": source_regular_sha,
        "dry_run": dry_run,
    }
    if dry_run:
        return plan

    target_root.parent.mkdir(parents=True, exist_ok=True)
    staging = target_root.parent / f".{target_root.name}.migration-{uuid.uuid4().hex}"
    try:
        staging.mkdir()
        target_mocks = staging / "mocks"
        shutil.copytree(source_mocks, target_mocks, symlinks=True, copy_function=shutil.copy2)
        shutil.copy2(source_results, staging / "results.jsonl")
        shutil.copy2(source_truth, staging / "truth_lcdm_d0.json")

        covariance_report = rewrite_covariance_links(
            target_mocks, covariances, expected_noisy
        )
        target_inventory = tree_inventory(target_mocks)
        target_regular_sha = regular_tree_digest(target_inventory)
        source_inventory_after = tree_inventory(source_mocks)
        if regular_tree_digest(source_inventory_after) != source_regular_sha:
            raise MigrationError("source mock tree changed during migration")
        if target_regular_sha != source_regular_sha:
            raise MigrationError("regular mock files changed during migration")
        if sha256_file(staging / "results.jsonl") != sha256_file(source_results):
            raise MigrationError("result ledger changed during migration")
        if sha256_file(staging / "truth_lcdm_d0.json") != sha256_file(source_truth):
            raise MigrationError("truth snapshot changed during migration")
        read_results(staging / "results.jsonl", expected_noisy)

        inventory_path = staging / "migration_inventory.json"
        inventory_path.write_text(
            json.dumps(target_inventory, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        migration_manifest = {
            "schema_version": "prd-null500-migration-v1",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "baseline_commit": baseline_commit,
            "baseline_tag": baseline_tag,
            "source": {
                "mock_root": relative_to_root(source_mocks),
                "mock_manifest_sha256": sha256_file(source_mocks / "mocks_manifest.json"),
                "regular_tree_sha256": source_regular_sha,
                "mock_indices": [0, expected_noisy],
                "noisy_indices": [1, expected_noisy],
            },
            "target": {
                "root": relative_to_root(target_root),
                "mock_root": f"{relative_to_root(target_root)}/mocks",
                "regular_tree_sha256": target_regular_sha,
            },
            "tracked_baseline_verification": git_verification,
            "result_rows": source_summary["result_rows"],
            "results_sha256": sha256_file(staging / "results.jsonl"),
            "truth_sha256": sha256_file(staging / "truth_lcdm_d0.json"),
            "covariance_links": covariance_report,
            "inventory": {
                "path": "migration_inventory.json",
                "entries": len(target_inventory),
                "sha256": sha256_file(inventory_path),
            },
            "validation": {
                "source_unchanged": True,
                "regular_files_byte_identical": True,
                "result_indices_complete_and_unique": True,
                "covariance_links_relative_and_resolved": True,
                "atomic_publish": True,
            },
        }
        (staging / "migration_manifest.json").write_text(
            json.dumps(migration_manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(staging, target_root)
        return migration_manifest
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise


def audit_target(
    target_root: Path = TARGET_ROOT,
    covariances: dict[str, Path] | None = None,
    expected_noisy: int = 100,
) -> dict:
    target_root = Path(target_root).resolve()
    covariances = {
        name: Path(path).resolve() for name, path in (covariances or DEFAULT_COVARIANCES).items()
    }
    manifest_path = target_root / "migration_manifest.json"
    inventory_path = target_root / "migration_inventory.json"
    for path in (manifest_path, inventory_path, target_root / "results.jsonl",
                 target_root / "truth_lcdm_d0.json", target_root / "mocks"):
        if not path.exists():
            raise MigrationError(f"migrated target is incomplete: {path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != "prd-null500-migration-v1":
        raise MigrationError(f"unexpected migration schema: {manifest.get('schema_version')}")
    if sha256_file(inventory_path) != manifest["inventory"]["sha256"]:
        raise MigrationError("migration inventory file hash mismatch")
    recorded_inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    current_inventory = tree_inventory(target_root / "mocks")
    if current_inventory != recorded_inventory:
        raise MigrationError("migrated mock inventory no longer matches recorded contents")
    regular_sha = regular_tree_digest(current_inventory)
    if regular_sha != manifest["target"]["regular_tree_sha256"]:
        raise MigrationError("migrated regular-tree hash mismatch")
    if sha256_file(target_root / "results.jsonl") != manifest["results_sha256"]:
        raise MigrationError("migrated result ledger hash mismatch")
    if sha256_file(target_root / "truth_lcdm_d0.json") != manifest["truth_sha256"]:
        raise MigrationError("migrated truth snapshot hash mismatch")
    rows = read_results(target_root / "results.jsonl", expected_noisy)
    for name, canonical in covariances.items():
        for k in range(expected_noisy + 1):
            link = target_root / "mocks" / f"m{k:03d}" / name
            if not link.is_symlink() or Path(os.readlink(link)).is_absolute():
                raise MigrationError(f"covariance link is not relative: {link}")
            if link.resolve() != canonical:
                raise MigrationError(f"covariance link does not resolve canonically: {link}")
    return {
        "audit": "PASS",
        "target": relative_to_root(target_root),
        "inventory_entries": len(current_inventory),
        "regular_tree_sha256": regular_sha,
        "result_rows": len(rows),
        "relative_covariance_links": len(covariances) * (expected_noisy + 1),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--audit", action="store_true")
    parser.add_argument("--source-mocks", type=Path, default=SOURCE_MOCKS)
    parser.add_argument("--source-results", type=Path, default=SOURCE_RESULTS)
    parser.add_argument("--source-truth", type=Path, default=SOURCE_TRUTH)
    parser.add_argument("--target-root", type=Path, default=TARGET_ROOT)
    args = parser.parse_args(argv)
    try:
        if args.audit:
            report = audit_target(target_root=args.target_root)
        else:
            report = migrate(
                source_mocks=args.source_mocks,
                source_results=args.source_results,
                source_truth=args.source_truth,
                target_root=args.target_root,
                dry_run=args.dry_run,
            )
    except (MigrationError, OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
