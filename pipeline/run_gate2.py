"""Run the CPL+P1 null-mock calibration in the isolated PRD extension tree.

Usage:
  .venv/bin/python pipeline/run_gate2.py [k_start k_end] [--jobs N]
  .venv/bin/python pipeline/run_gate2.py 101 500 --jobs 4 --dry-run

The default campaign root is ``runs/prd_extension/null500``. CLI runs are
refused outside ``runs/prd_extension`` so that the completed v1.x products in
``runs/gate2`` cannot be changed accidentally.

Resume-safe: mocks with an existing result line in the selected campaign's
``results.jsonl`` are skipped. MCMC uses one chain per mock (calibration
machinery; paper chains use four).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
EXTENSION_RESULTS_ROOT = ROOT / "runs" / "prd_extension"
DEFAULT_RUN_ROOT = EXTENSION_RESULTS_ROOT / "null500"
COBAYA = Path(sys.executable).with_name("cobaya-run.exe" if os.name == "nt" else "cobaya-run")

REQUIRED_MOCK_INPUTS = (
    "cmb_mean.json",
    "config.dataset",
    "sn_mock.dat",
    "sn_cov.cov",
    "bao_mean.txt",
    "bao_cov.txt",
)

classify_lock = threading.Lock()
write_lock = threading.Lock()


@dataclass(frozen=True)
class RunPaths:
    """All mutable paths for one null-mock campaign."""

    run_root: Path
    mocks: Path
    results: Path

    @classmethod
    def from_root(cls, run_root: str | os.PathLike[str]) -> "RunPaths":
        root = Path(run_root)
        if not root.is_absolute():
            root = ROOT / root
        root = root.resolve(strict=False)
        return cls(root, root / "mocks", root / "results.jsonl")


def require_extension_run_root(run_root: str | os.PathLike[str]) -> Path:
    """Resolve and reject any CLI output root outside the PRD extension tree."""

    resolved = RunPaths.from_root(run_root).run_root
    extension = EXTENSION_RESULTS_ROOT.resolve(strict=False)
    try:
        relative = resolved.relative_to(extension)
    except ValueError as exc:
        raise ValueError(
            f"refusing campaign root outside {extension}: {resolved}; "
            "the completed v1.x runs are read-only"
        ) from exc
    if relative == Path("."):
        raise ValueError(
            f"campaign root must be a named directory below {extension}; "
            f"use {DEFAULT_RUN_ROOT} for WP2"
        )
    return resolved


def validate_range(k0: int, k1: int, jobs: int) -> None:
    if not 1 <= k0 <= k1 <= 500:
        raise ValueError(
            f"WP2 noisy mock range must satisfy 1 <= start <= end <= 500: {k0}..{k1}"
        )
    if jobs < 1:
        raise ValueError(f"jobs must be positive: {jobs}")


def done_ks(results: str | os.PathLike[str]) -> set[int]:
    """Return completed indices from only the selected campaign ledger."""

    completed: set[int] = set()
    path = Path(results)
    if path.exists():
        with path.open(encoding="utf-8") as stream:
            for line in stream:
                try:
                    completed.add(int(json.loads(line)["k"]))
                except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                    pass
    return completed


def pending_ks(paths: RunPaths, k0: int, k1: int) -> list[int]:
    completed = done_ks(paths.results)
    return [k for k in range(k0, k1 + 1) if k not in completed]


def preflight(paths: RunPaths, indices: list[int]) -> None:
    """Fail before production if the isolated input tree is incomplete."""

    if not COBAYA.is_file():
        raise FileNotFoundError(
            f"cobaya-run is missing beside the active Python interpreter: {COBAYA}"
        )
    if not paths.mocks.is_dir():
        raise FileNotFoundError(
            f"isolated mock tree is missing: {paths.mocks}; "
            "stage and audit the v1.x inputs there before running WP2"
        )
    resolved_root = paths.run_root.resolve(strict=False)
    resolved_mocks = paths.mocks.resolve(strict=False)
    resolved_results = paths.results.resolve(strict=False)
    for label, resolved in (("mock tree", resolved_mocks), ("result ledger", resolved_results)):
        try:
            resolved.relative_to(resolved_root)
        except ValueError as exc:
            raise ValueError(f"{label} escapes isolated campaign root: {resolved}") from exc
    manifest = paths.mocks / "mocks_manifest.json"
    if not manifest.is_file():
        raise FileNotFoundError(f"isolated mock manifest is missing: {manifest}")

    missing: list[Path] = []
    for k in indices:
        mock_dir = paths.mocks / f"m{k:03d}"
        try:
            mock_dir.resolve(strict=False).relative_to(resolved_mocks)
        except ValueError as exc:
            raise ValueError(f"mock directory escapes isolated mock tree: {mock_dir}") from exc
        mutable = [mock_dir / "run.yaml", mock_dir / "run.log", *mock_dir.glob("chain*")]
        linked = [path for path in mutable if path.is_symlink()]
        if linked:
            raise ValueError(f"mutable production files may not be symlinks: {linked[0]}")
        for name in REQUIRED_MOCK_INPUTS:
            candidate = mock_dir / name
            if not candidate.is_file():
                missing.append(candidate)
                if len(missing) == 10:
                    break
        if len(missing) == 10:
            break
    if missing:
        preview = ", ".join(str(path) for path in missing)
        raise FileNotFoundError(
            f"isolated mock inputs are incomplete (first {len(missing)}): {preview}"
        )


def make_yaml(k: int, paths: RunPaths) -> tuple[Path, Path]:
    from cobaya.yaml import yaml_dump, yaml_load_file

    mock_dir = paths.mocks / f"m{k:03d}"
    with (mock_dir / "cmb_mean.json").open(encoding="utf-8") as stream:
        cmb_mean = json.load(stream)["mean"]
    info = yaml_load_file(str(HERE / "d0_cpl_p1.yaml"))
    info["packages_path"] = str(ROOT / "data" / "cobaya_packages")
    info["likelihood"]["sn.pantheonplusshoes"] = {
        "path": str(mock_dir),
        "dataset_file": "config.dataset",
        "use_abs_mag": True,
    }
    info["likelihood"]["bao.desi_dr2.desi_bao_all"] = {
        "path": str(mock_dir),
        "measurements_file": "bao_mean.txt",
        "cov_file": "bao_cov.txt",
        "rs_fid": 1,
    }
    info["likelihood"]["pipeline.cmb_distprior.PlanckDistPrior"]["mean"] = cmb_mean
    info["sampler"]["mcmc"].update(seed=3000 + k)
    info["sampler"]["mcmc"]["max_samples"] = 300000
    info["output"] = str(mock_dir / "chain")
    yaml_path = mock_dir / "run.yaml"
    yaml_path.write_text(yaml_dump(info), encoding="utf-8")
    return mock_dir, yaml_path


def run_one(k: int, paths: RunPaths) -> dict:
    mock_dir, yaml_path = make_yaml(k, paths)
    chain_txt = mock_dir / "chain.1.txt"
    checkpoint = mock_dir / "chain.checkpoint"
    log = mock_dir / "run.log"
    if not chain_txt.exists() or checkpoint.exists():
        with log.open("w", encoding="utf-8") as stream:
            result = subprocess.run(
                [str(COBAYA), str(yaml_path), "--force"],
                stdout=stream,
                stderr=stream,
                check=False,
            )
        if result.returncode != 0:
            return {"k": k, "error": f"cobaya exit {result.returncode}"}

    with classify_lock:
        from pipeline.classify_posterior import main as classify

        out = classify(str(mock_dir / "chain"))
    labels = ("CRUNCH", "RIP", "DS", "DECAY", "OTHER")
    record = {
        "k": k,
        "P": {label: out[label]["P"] for label in labels},
        "mc_err": {label: out[label]["mc_err"] for label in labels},
        "P_heat": out["P_heat_death_compatible"],
        "boundary_fraction": out["boundary_fraction"],
        "n_samples": out["n_samples"],
    }
    with write_lock:
        with paths.results.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record) + "\n")
    return record


def main(
    k0: int = 101,
    k1: int = 500,
    jobs: int = 4,
    run_root: str | os.PathLike[str] = DEFAULT_RUN_ROOT,
    dry_run: bool = False,
) -> list[int]:
    validate_range(k0, k1, jobs)
    paths = RunPaths.from_root(require_extension_run_root(run_root))
    indices = pending_ks(paths, k0, k1)
    preflight(paths, indices)
    print(f"campaign root: {paths.run_root}")
    print(f"running {len(indices)} mocks with {jobs} workers")
    if dry_run:
        print("dry-run: inputs complete; no YAML, chain, log, or result was written")
        return indices

    with ThreadPoolExecutor(max_workers=jobs) as executor:
        for record in executor.map(lambda k: run_one(k, paths), indices):
            tag = (
                "ERR"
                if "error" in record
                else f"P_heat={record['P_heat']:.4f} P_RIP={record['P']['RIP']:.4f}"
            )
            print(f"mock {record['k']:3d}: {tag}", flush=True)
    return indices


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("k_start", nargs="?", type=int, default=101)
    parser.add_argument("k_end", nargs="?", type=int, default=500)
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument(
        "--run-root",
        default=str(DEFAULT_RUN_ROOT.relative_to(ROOT)),
        help="campaign directory below runs/prd_extension (default: %(default)s)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="validate inputs and print the plan only"
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = parse_args()
    try:
        main(args.k_start, args.k_end, args.jobs, args.run_root, args.dry_run)
    except (FileNotFoundError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
