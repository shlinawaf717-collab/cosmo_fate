"""Run the registered WP3 off-boundary power campaign.

The six Asimov diagnostics use k=0.  The 600 confirmatory noisy mocks use
k=1..100.  Sampler seeds are frozen as 310000 + 1000*j + k, where j is the
one-based truth ordinal in TRUTHS.

Examples
--------
  .venv/bin/python pipeline/run_wp3.py --asimov-only --jobs 6
  .venv/bin/python pipeline/run_wp3.py --noisy-only --jobs 6
  .venv/bin/python pipeline/run_wp3.py --dry-run --jobs 6

The result ledger is append-only and resume-safe.  A completed (truth_id, k)
pair is skipped.  WP3 calibration uses one chain per mock, matching WP2.
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
RUN_ROOT = ROOT / "runs" / "prd_extension" / "wp3_power"
RESULTS = RUN_ROOT / "results.jsonl"
COBAYA = Path(sys.executable).with_name("cobaya-run.exe" if os.name == "nt" else "cobaya-run")

TRUTHS = (
    ("wam060", -0.60),
    ("wam030", -0.30),
    ("wam015", -0.15),
    ("wap015", +0.15),
    ("wap030", +0.30),
    ("wap060", +0.60),
)
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


@dataclass(frozen=True, order=True)
class Case:
    truth_id: str
    truth_ordinal: int
    wa_truth: float
    k: int

    @property
    def seed(self) -> int:
        return 310000 + 1000 * self.truth_ordinal + self.k

    @property
    def mock_dir(self) -> Path:
        return RUN_ROOT / self.truth_id / "mocks" / f"m{self.k:03d}"


def requested_cases(asimov_only: bool = False, noisy_only: bool = False) -> list[Case]:
    if asimov_only and noisy_only:
        raise ValueError("--asimov-only and --noisy-only are mutually exclusive")
    ks = range(0, 1) if asimov_only else range(1, 101) if noisy_only else range(0, 101)
    return [
        Case(truth_id, ordinal, wa_truth, k)
        for ordinal, (truth_id, wa_truth) in enumerate(TRUTHS, start=1)
        for k in ks
    ]


def completed_cases(path: Path = RESULTS) -> set[tuple[str, int]]:
    completed: set[tuple[str, int]] = set()
    if not path.exists():
        return completed
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            try:
                record = json.loads(line)
                if "error" not in record:
                    completed.add((str(record["truth_id"]), int(record["k"])))
            except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                continue
    return completed


def pending_cases(cases: list[Case], path: Path = RESULTS) -> list[Case]:
    completed = completed_cases(path)
    return [case for case in cases if (case.truth_id, case.k) not in completed]


def preflight(cases: list[Case]) -> None:
    if not COBAYA.is_file():
        raise FileNotFoundError(f"cobaya-run is missing: {COBAYA}")
    resolved_extension = (ROOT / "runs" / "prd_extension").resolve()
    resolved_root = RUN_ROOT.resolve()
    try:
        resolved_root.relative_to(resolved_extension)
    except ValueError as exc:
        raise ValueError(f"WP3 run root escapes the PRD extension: {resolved_root}") from exc

    campaign_manifest = RUN_ROOT / "mock_campaign_manifest.json"
    if not campaign_manifest.is_file():
        raise FileNotFoundError(f"WP3 mock audit is missing: {campaign_manifest}")
    with campaign_manifest.open(encoding="utf-8") as stream:
        audit = json.load(stream)
    if audit.get("status") != "PASS":
        raise ValueError("WP3 mock campaign audit has not passed")

    missing: list[Path] = []
    for case in cases:
        mock_dir = case.mock_dir
        try:
            mock_dir.resolve().relative_to(resolved_root)
        except ValueError as exc:
            raise ValueError(f"mock directory escapes WP3 root: {mock_dir}") from exc
        mutable = [mock_dir / "run.yaml", mock_dir / "run.log", *mock_dir.glob("chain*")]
        linked = [path for path in mutable if path.is_symlink()]
        if linked:
            raise ValueError(f"mutable production file may not be a symlink: {linked[0]}")
        for name in REQUIRED_MOCK_INPUTS:
            candidate = mock_dir / name
            if not candidate.is_file():
                missing.append(candidate)
                if len(missing) >= 10:
                    break
        if len(missing) >= 10:
            break
    if missing:
        raise FileNotFoundError(
            "WP3 inputs are incomplete (first entries): " + ", ".join(map(str, missing))
        )


def make_yaml(case: Case) -> Path:
    from cobaya.yaml import yaml_dump, yaml_load_file

    mock_dir = case.mock_dir
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
    info["sampler"]["mcmc"].update(seed=case.seed, max_samples=300000)
    info["output"] = str(mock_dir / "chain")
    yaml_path = mock_dir / "run.yaml"
    yaml_path.write_text(yaml_dump(info), encoding="utf-8")
    return yaml_path


def run_one(case: Case) -> dict:
    yaml_path = make_yaml(case)
    mock_dir = case.mock_dir
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
            return {
                "truth_id": case.truth_id,
                "wa_truth": case.wa_truth,
                "k": case.k,
                "seed": case.seed,
                "error": f"cobaya exit {result.returncode}",
            }

    with classify_lock:
        from pipeline.classify_posterior import main as classify

        out = classify(str(mock_dir / "chain"))
    labels = ("CRUNCH", "RIP", "DS", "DECAY", "OTHER")
    record = {
        "truth_id": case.truth_id,
        "truth_ordinal": case.truth_ordinal,
        "wa_truth": case.wa_truth,
        "k": case.k,
        "kind": "asimov" if case.k == 0 else "noisy",
        "seed": case.seed,
        "P": {label: out[label]["P"] for label in labels},
        "mc_err": {label: out[label]["mc_err"] for label in labels},
        "P_heat": out["P_heat_death_compatible"],
        "boundary_fraction": out["boundary_fraction"],
        "n_samples": out["n_samples"],
    }
    with write_lock:
        with RESULTS.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, sort_keys=True) + "\n")
    return record


def main(
    jobs: int = 6,
    asimov_only: bool = False,
    noisy_only: bool = False,
    dry_run: bool = False,
) -> list[Case]:
    if jobs < 1:
        raise ValueError(f"jobs must be positive: {jobs}")
    cases = pending_cases(requested_cases(asimov_only, noisy_only))
    preflight(cases)
    kind = "Asimov" if asimov_only else "noisy" if noisy_only else "all"
    print(f"WP3 root: {RUN_ROOT}")
    print(f"running {len(cases)} pending {kind} cases with {jobs} workers")
    if dry_run:
        print("dry-run: all inputs passed; no inference file was written")
        return cases

    with ThreadPoolExecutor(max_workers=jobs) as executor:
        for record in executor.map(run_one, cases):
            if "error" in record:
                tag = f"ERR {record['error']}"
            else:
                tag = f"P_heat={record['P_heat']:.4f} P_RIP={record['P']['RIP']:.4f}"
            print(
                f"{record['truth_id']} m{record['k']:03d} "
                f"seed={record['seed']}: {tag}",
                flush=True,
            )
    return cases


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--asimov-only", action="store_true")
    group.add_argument("--noisy-only", action="store_true")
    parser.add_argument("--jobs", type=int, default=6)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = parse_args()
    main(
        jobs=args.jobs,
        asimov_only=args.asimov_only,
        noisy_only=args.noisy_only,
        dry_run=args.dry_run,
    )
