"""Generate and audit the six registered WP3 mock ensembles."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.fit_wp3_truths import TRUTH_SPECS, WP3_ROOT, sha256_file
from pipeline.make_mocks import initialize_mocks, production_assets, sha256_obj
from pipeline.migrate_null500 import DEFAULT_COVARIANCES


TRUTH_GRID_MANIFEST = WP3_ROOT / "truth_grid_manifest.json"


class WP3MockError(RuntimeError):
    pass


def _truth_path(truth_id: str) -> Path:
    return WP3_ROOT / "truths" / truth_id / "truth.json"


def _generate_one(spec: tuple[str, float, int, int]) -> dict:
    truth_id, wa, generator_seed, _ = spec
    truth_path = _truth_path(truth_id)
    truth = json.loads(truth_path.read_text(encoding="utf-8"))
    if truth.get("truth_id") != truth_id or float(truth.get("wa")) != wa:
        raise WP3MockError(f"{truth_id}: frozen truth metadata mismatch")
    mocks_root = WP3_ROOT / truth_id / "mocks"
    if mocks_root.exists():
        manifest_path = mocks_root / "mocks_manifest.json"
        if not manifest_path.is_file():
            raise WP3MockError(f"{truth_id}: refusing unrecognized existing mock tree")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if (
            manifest.get("n") != 100
            or manifest.get("seed") != generator_seed
            or manifest.get("truth_fingerprint") != sha256_obj(truth)
        ):
            raise WP3MockError(f"{truth_id}: existing mock manifest mismatch")
        return {
            "truth_id": truth_id,
            "already_generated": True,
            "manifest": manifest_path,
        }
    assets = production_assets(truth)
    manifest = initialize_mocks(
        mocks_root,
        truth,
        n_mocks=100,
        seed=generator_seed,
        assets=assets,
    )
    return {
        "truth_id": truth_id,
        "already_generated": False,
        "manifest": mocks_root / "mocks_manifest.json",
        "cmb_truth_pred": manifest["cmb_truth_pred"],
    }


def generate_campaign(jobs: int = 2) -> dict:
    if jobs < 1:
        raise WP3MockError("jobs must be positive")
    if not TRUTH_GRID_MANIFEST.is_file():
        raise WP3MockError("frozen truth-grid manifest is missing")
    truth_grid = json.loads(TRUTH_GRID_MANIFEST.read_text(encoding="utf-8"))
    for truth_id, digest in truth_grid["truth_sha256"].items():
        if sha256_file(_truth_path(truth_id)) != digest:
            raise WP3MockError(f"{truth_id}: frozen truth hash mismatch")
    with ThreadPoolExecutor(max_workers=jobs) as executor:
        generated = list(executor.map(_generate_one, TRUTH_SPECS))
    report = audit_campaign()
    report["generation"] = {
        "jobs": jobs,
        "newly_generated": [
            row["truth_id"] for row in generated if not row["already_generated"]
        ],
    }
    manifest_path = WP3_ROOT / "mock_campaign_manifest.json"
    manifest_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


def _assert_asimov(truth: dict, truth_id: str, mocks_root: Path) -> None:
    import pandas as pd

    assets = production_assets(truth)
    m000 = mocks_root / "m000"
    sn = pd.read_csv(m000 / "sn_mock.dat", sep=r"\s+")
    # pandas' decimal round-trip can move a binary64 value by one ulp.
    if not np.allclose(
        sn["m_b_corr"].to_numpy()[assets["sn_mask"]],
        np.asarray(assets["sn_mu"])[assets["sn_mask"]],
        rtol=0,
        atol=5e-15,
    ):
        raise WP3MockError(f"{truth_id}: Asimov SN input differs from truth prediction")
    cmb = np.asarray(
        json.loads((m000 / "cmb_mean.json").read_text(encoding="utf-8"))["mean"],
        dtype=float,
    )
    if not np.array_equal(cmb, np.asarray(assets["cmb_mu"])):
        raise WP3MockError(f"{truth_id}: Asimov CMB input differs from truth prediction")
    bao_rows = [
        line.split()
        for line in (m000 / "bao_mean.txt").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]
    bao_values = np.asarray([float(row[1]) for row in bao_rows])
    # BAO files intentionally store eight decimals.
    if not np.allclose(bao_values, assets["bao_mu"], rtol=0, atol=5.1e-9):
        raise WP3MockError(f"{truth_id}: Asimov BAO input differs from truth prediction")


def audit_campaign() -> dict:
    truths = {}
    total_dirs = 0
    total_links = 0
    input_fingerprints = []
    for truth_id, wa, generator_seed, _ in TRUTH_SPECS:
        truth_path = _truth_path(truth_id)
        truth = json.loads(truth_path.read_text(encoding="utf-8"))
        mocks_root = WP3_ROOT / truth_id / "mocks"
        manifest_path = mocks_root / "mocks_manifest.json"
        if not manifest_path.is_file():
            raise WP3MockError(f"{truth_id}: mock manifest missing")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if (
            manifest.get("n") != 100
            or manifest.get("seed") != generator_seed
            or manifest.get("truth_fingerprint") != sha256_obj(truth)
            or float(manifest["truth"]["wa"]) != wa
        ):
            raise WP3MockError(f"{truth_id}: mock manifest failed frozen checks")
        actual = {
            path.name
            for path in mocks_root.iterdir()
            if path.is_dir() and path.name.startswith("m") and path.name[1:].isdigit()
        }
        expected = {f"m{k:03d}" for k in range(101)}
        if actual != expected:
            raise WP3MockError(
                f"{truth_id}: mock directory mismatch; "
                f"missing={sorted(expected - actual)}, extra={sorted(actual - expected)}"
            )
        for k in range(101):
            mock_dir = mocks_root / f"m{k:03d}"
            for name, canonical in DEFAULT_COVARIANCES.items():
                link = mock_dir / name
                if (
                    not link.is_symlink()
                    or Path(os.readlink(link)).is_absolute()
                    or link.resolve() != canonical.resolve()
                ):
                    raise WP3MockError(
                        f"{truth_id} m{k:03d}: invalid covariance link {name}"
                    )
                total_links += 1
            for required in (
                "sn_mock.dat",
                "config.dataset",
                "bao_mean.txt",
                "cmb_mean.json",
            ):
                if not (mock_dir / required).is_file():
                    raise WP3MockError(
                        f"{truth_id} m{k:03d}: missing input {required}"
                    )
        _assert_asimov(truth, truth_id, mocks_root)
        total_dirs += len(actual)
        input_fingerprints.append(manifest["input_fingerprint"])
        truths[truth_id] = {
            "wa": wa,
            "generator_seed": generator_seed,
            "truth_sha256": sha256_file(truth_path),
            "mock_manifest_sha256": sha256_file(manifest_path),
            "mock_directories": len(actual),
            "asimov_input_check": "PASS",
        }
    if any(item != input_fingerprints[0] for item in input_fingerprints[1:]):
        raise WP3MockError("WP3 truth points do not share one input-data fingerprint")
    return {
        "schema_version": "wp3-mock-campaign-v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "PASS",
        "truths": truths,
        "total_mock_directories": total_dirs,
        "total_noisy_mocks": 600,
        "total_asimov_mocks": 6,
        "relative_covariance_links": total_links,
        "shared_input_fingerprint": input_fingerprints[0],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=int, default=2)
    parser.add_argument("--audit", action="store_true")
    args = parser.parse_args(argv)
    report = audit_campaign() if args.audit else generate_campaign(args.jobs)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
