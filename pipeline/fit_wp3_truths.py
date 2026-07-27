"""Fit and freeze the six constrained CPL truths registered for WP3."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cobaya.yaml import yaml_dump, yaml_load_file


WP3_ROOT = ROOT / "runs" / "prd_extension" / "wp3_power"
TRUTHS_ROOT = WP3_ROOT / "truths"
BASE_CONFIG = ROOT / "pipeline" / "d0_cpl_p1.yaml"
COBAYA = Path(sys.executable).with_name(
    "cobaya-run.exe" if os.name == "nt" else "cobaya-run"
)
TRUTH_SPECS = (
    ("wam060", -0.60, 2026072201, 2026072301),
    ("wam030", -0.30, 2026072202, 2026072302),
    ("wam015", -0.15, 2026072203, 2026072303),
    ("wap015", +0.15, 2026072204, 2026072304),
    ("wap030", +0.30, 2026072205, 2026072305),
    ("wap060", +0.60, 2026072206, 2026072306),
)
FREE_PARAMETERS = ("ombh2", "omegam", "H0", "w", "Mb")
DERIVED_PARAMETERS = ("omch2", "rdrag")


class WP3TruthError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_truth_config(
    truth_id: str,
    wa: float,
    optimizer_seed: int,
    truths_root: Path = TRUTHS_ROOT,
) -> tuple[dict, Path, Path]:
    info = yaml_load_file(str(BASE_CONFIG))
    truth_dir = Path(truths_root) / truth_id
    output_root = truth_dir / "fit"
    info["packages_path"] = str(ROOT / "data" / "cobaya_packages")
    info["likelihood"]["pipeline.cmb_distprior.PlanckDistPrior"]["python_path"] = str(
        ROOT
    )
    info.pop("prior", None)
    info["params"]["wa"] = float(wa)
    # Enforce the registered early-time matter-dominance condition as a hard
    # sampled-parameter bound while maximizing the likelihood.
    w_info = info["params"]["w"]
    w_info["prior"] = dict(w_info["prior"])
    w_info["prior"]["max"] = min(float(w_info["prior"]["max"]), -float(wa) - 1e-8)
    if w_info["prior"]["max"] <= float(w_info["prior"]["min"]):
        raise WP3TruthError(f"{truth_id}: empty constrained w interval")
    info["sampler"] = {
        "minimize": {
            "ignore_prior": True,
            "best_of": 8,
            "seed": int(optimizer_seed),
            "override_bobyqa": {"rhoend": 1e-5},
        }
    }
    info["output"] = str(output_root)
    config_path = truth_dir / "fit.yaml"
    return info, config_path, output_root


def prepare_configs(truths_root: Path = TRUTHS_ROOT) -> list[dict]:
    truths_root = Path(truths_root).resolve(strict=False)
    try:
        truths_root.relative_to(
            (ROOT / "runs" / "prd_extension" / "wp3_power").resolve()
        )
    except ValueError as exc:
        raise WP3TruthError(f"truth root escapes WP3 tree: {truths_root}") from exc
    prepared = []
    for ordinal, (truth_id, wa, generator_seed, optimizer_seed) in enumerate(
        TRUTH_SPECS, 1
    ):
        info, config_path, output_root = build_truth_config(
            truth_id, wa, optimizer_seed, truths_root
        )
        config_path.parent.mkdir(parents=True, exist_ok=True)
        if (config_path.parent / "truth.json").exists():
            prepared.append(
                {
                    "truth_id": truth_id,
                    "wa": wa,
                    "ordinal": ordinal,
                    "generator_seed": generator_seed,
                    "optimizer_seed": optimizer_seed,
                    "config": str(config_path),
                    "output": str(output_root),
                    "already_frozen": True,
                }
            )
            continue
        config_path.write_text(yaml_dump(info), encoding="utf-8")
        prepared.append(
            {
                "truth_id": truth_id,
                "wa": wa,
                "ordinal": ordinal,
                "generator_seed": generator_seed,
                "optimizer_seed": optimizer_seed,
                "config": str(config_path),
                "output": str(output_root),
                "already_frozen": False,
            }
        )
    return prepared


def parse_bestfit(path: Path) -> dict[str, float]:
    lines = [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    header = next((line[1:].split() for line in lines if line.startswith("#")), None)
    values_line = next((line for line in lines if not line.startswith("#")), None)
    if not header or values_line is None:
        raise WP3TruthError(f"invalid best-fit table: {path}")
    values = values_line.split()
    if len(header) != len(values):
        raise WP3TruthError(
            f"best-fit column mismatch: {path}: {len(header)} != {len(values)}"
        )
    return {name: float(value) for name, value in zip(header, values)}


def freeze_truth(spec: dict) -> dict:
    truth_id = spec["truth_id"]
    truth_dir = Path(spec["config"]).parent
    truth_path = truth_dir / "truth.json"
    if truth_path.exists():
        return json.loads(truth_path.read_text(encoding="utf-8"))
    log_path = truth_dir / "fit.log"
    with log_path.open("w", encoding="utf-8") as stream:
        result = subprocess.run(
            [str(COBAYA), spec["config"], "--force"],
            cwd=ROOT,
            stdout=stream,
            stderr=stream,
            check=False,
        )
    if result.returncode != 0:
        raise WP3TruthError(
            f"{truth_id}: cobaya minimizer exited {result.returncode}; see {log_path}"
        )
    bestfit_path = Path(spec["output"] + ".bestfit.txt")
    if not bestfit_path.is_file():
        raise WP3TruthError(f"{truth_id}: missing best-fit output {bestfit_path}")
    row = parse_bestfit(bestfit_path)
    missing = [
        name
        for name in (*FREE_PARAMETERS, *DERIVED_PARAMETERS, "chi2")
        if name not in row
    ]
    if missing:
        raise WP3TruthError(f"{truth_id}: best-fit columns missing {missing}")
    truth = {name: row[name] for name in (*FREE_PARAMETERS, *DERIVED_PARAMETERS)}
    truth["wa"] = float(spec["wa"])
    if truth["w"] + truth["wa"] >= 0:
        raise WP3TruthError(f"{truth_id}: fitted truth violates w + wa < 0")
    if truth["omch2"] <= 0:
        raise WP3TruthError(f"{truth_id}: fitted truth has non-positive omch2")
    likelihood_chi2 = {
        name.removeprefix("chi2__"): value
        for name, value in row.items()
        if name.startswith("chi2__")
    }
    frozen = {
        **truth,
        "truth_id": truth_id,
        "truth_ordinal": spec["ordinal"],
        "generator_seed": spec["generator_seed"],
        "optimizer": {
            "method": "bobyqa",
            "best_of": 8,
            "seed": spec["optimizer_seed"],
            "rhoend": 1e-5,
            "ignore_prior": True,
            "hard_constraint": f"w < {-float(spec['wa']):.8g}",
        },
        "fit": {
            "chi2": row["chi2"],
            "minuslogpost": row.get("minuslogpost"),
            "likelihood_chi2": likelihood_chi2,
        },
        "provenance": {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "base_config": str(BASE_CONFIG.relative_to(ROOT)),
            "base_config_sha256": sha256_file(BASE_CONFIG),
            "fit_config": str(Path(spec["config"]).relative_to(ROOT)),
            "fit_config_sha256": sha256_file(Path(spec["config"])),
            "bestfit": str(bestfit_path.relative_to(ROOT)),
            "bestfit_sha256": sha256_file(bestfit_path),
            "fit_log": str(log_path.relative_to(ROOT)),
            "requirements_lock_sha256": sha256_file(ROOT / "requirements.lock"),
        },
    }
    truth_path.write_text(
        json.dumps(frozen, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return frozen


def run_truth_fits(truths_root: Path = TRUTHS_ROOT, jobs: int = 2) -> dict:
    if jobs < 1:
        raise WP3TruthError("jobs must be positive")
    specs = prepare_configs(truths_root)
    with ThreadPoolExecutor(max_workers=jobs) as executor:
        truths = list(executor.map(freeze_truth, specs))
    truth_hashes = {
        truth["truth_id"]: sha256_file(
            Path(truths_root) / truth["truth_id"] / "truth.json"
        )
        for truth in truths
    }
    report = {
        "schema_version": "wp3-truth-grid-v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "truth_ids": [spec[0] for spec in TRUTH_SPECS],
        "wa": [spec[1] for spec in TRUTH_SPECS],
        "generator_seeds": [spec[2] for spec in TRUTH_SPECS],
        "optimizer_seeds": [spec[3] for spec in TRUTH_SPECS],
        "truth_sha256": truth_hashes,
        "status": "FROZEN",
    }
    manifest = Path(truths_root).parent / "truth_grid_manifest.json"
    manifest.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--truths-root", type=Path, default=TRUTHS_ROOT)
    parser.add_argument("--jobs", type=int, default=2)
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args(argv)
    if args.prepare_only:
        report = prepare_configs(args.truths_root)
    else:
        report = run_truth_fits(args.truths_root, args.jobs)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
