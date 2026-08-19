#!/usr/bin/env python3
"""Freeze two official DESI DR1 likelihood reference evaluations."""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from cobaya.yaml import yaml_dump

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.audit_wp4_f0_reproduction import atomic_write_json, sha256_file


RUN = ROOT / "runs/prd_extension/wp6_growth/reference"
DATA = ROOT / "data/wp6_desi_dr1/likelihood"
BESTFIT = ROOT / "data/wp6_desi_dr1/reference/bestfit.minimum.txt"
PLAN = RUN / "benchmark_plan.json"
BESTFIT_SHA256 = "8d4f1d65b0a932d37f142ae6d18397c38f8d1451bad00aba5f4caf35323e86c9"
BESTFIT_URL = (
    "https://data.desi.lbl.gov/public/dr1/vac/dr1/full-shape-cosmo-params/"
    "v1.0/iminuit/base_w_wa/"
    "desi-reptvelocileptors-fs-bao-all_pantheonplus_planck2018-lowl-TT-clik_"
    "planck2018-lowl-EE-clik_planck2018-highl-plik-TTTEEE_planck-act-dr6-lensing/"
    "bestfit.minimum.txt"
)


def _read_bestfit() -> dict[str, float]:
    if sha256_file(BESTFIT) != BESTFIT_SHA256:
        raise RuntimeError("official DR1 MAP reference hash mismatch")
    lines = [line.strip() for line in BESTFIT.read_text().splitlines() if line.strip()]
    names = lines[0].removeprefix("#").split()
    values = [float(value) for value in lines[1].split()]
    if len(names) != len(values):
        raise RuntimeError("official DR1 MAP reference columns are malformed")
    return dict(zip(names, values))


def _components() -> tuple[dict, dict]:
    theory = {
        "camb": {
            "extra_args": {
                "bbn_predictor": "PArthENoPE_880.2_standard.dat",
                "dark_energy_model": "ppf",
                "num_massive_neutrinos": 1,
            },
            "stop_at_error": True,
        },
        "pipeline.wp6_desi_fs.DESIDR1ReptVelocileptors": {
            "python_path": str(ROOT),
            "is_physical_prior": True,
            "stop_at_error": True,
        },
    }
    likelihood = {
        "pipeline.wp6_desi_fs.DESIDR1FSBAO": {
            "python_path": str(ROOT),
            "data_dir": str(DATA),
            "observable_name": "spectrum-poles-rotated+bao-recon",
            "tracers": [
                "bgs_z0", "lrg_z0", "lrg_z1", "lrg_z2",
                "elg_z1", "qso_z0", "lya_z0",
            ],
            "solve": "marg",
            "stop_at_error": True,
        }
    }
    return theory, likelihood


def _info(params: dict, name: str) -> dict:
    theory, likelihood = _components()
    return {
        "packages_path": str(ROOT / "data/cobaya_packages"),
        "theory": theory,
        "likelihood": likelihood,
        "params": params | {
            "chi2__FS_BAO": {"latex": r"\chi^2_\mathrm{FS+BAO}", "derived": True}
        },
        "sampler": {"evaluate": {"N": 1}},
        "output": str(RUN / "outputs" / name / "chain"),
        "force": True,
    }


def _public_example_params() -> dict:
    return {
        "omch2": {"value": "lambda omegam, ombh2, H0: omegam*(H0/100)**2 - ombh2"},
        "H0": 68.5,
        "omegam": 0.304158,
        "ombh2": 0.0189629,
        "logA": 3.0,
        "As": {"value": "lambda logA: 1e-10*np.exp(logA)"},
        "mnu": 0.06,
        "nnu": 3.044,
        "w": -1.0,
        "wa": 0.0,
        "omk": 0.0,
        "pre_QSO_z0.b1p": 0.780983,
        "pre_QSO_z0.b2p": 0.353843,
        "pre_QSO_z0.bsp": 0.135725,
        "pre_ELG_z1.b1p": 0.127936,
        "pre_ELG_z1.b2p": -0.578801,
        "pre_ELG_z1.bsp": -1.45356,
        "pre_LRG_z2.b1p": 1.04564,
        "pre_LRG_z2.b2p": -0.493139,
        "pre_LRG_z2.bsp": -0.24021,
        "pre_LRG_z1.b1p": 1.22446,
        "pre_LRG_z1.b2p": -0.671727,
        "pre_LRG_z1.bsp": -0.22624,
        "pre_LRG_z0.b1p": 1.1351,
        "pre_LRG_z0.b2p": -0.139101,
        "pre_LRG_z0.bsp": -0.910397,
        "pre_BGS_z0.b1p": 1.11348,
        "pre_BGS_z0.b2p": 0.660148,
        "pre_BGS_z0.bsp": -0.223088,
    }


def _official_map_params(row: dict[str, float]) -> dict:
    names = [
        "logA", "ns", "ombh2", "omch2", "tau", "w", "wa",
        "pre_QSO_z0.b1p", "pre_QSO_z0.b2p", "pre_QSO_z0.bsp",
        "pre_ELG_z1.b1p", "pre_ELG_z1.b2p", "pre_ELG_z1.bsp",
        "pre_LRG_z2.b1p", "pre_LRG_z2.b2p", "pre_LRG_z2.bsp",
        "pre_LRG_z1.b1p", "pre_LRG_z1.b2p", "pre_LRG_z1.bsp",
        "pre_LRG_z0.b1p", "pre_LRG_z0.b2p", "pre_LRG_z0.bsp",
        "pre_BGS_z0.b1p", "pre_BGS_z0.b2p", "pre_BGS_z0.bsp",
    ]
    params = {name: row[name] for name in names}
    params |= {
        "H0": row["H0"],
        "As": {"value": "lambda logA: 1e-10*np.exp(logA)"},
        "mnu": 0.06,
        "nnu": 3.044,
        "omk": 0.0,
    }
    return params


def prepare() -> dict:
    if PLAN.is_file():
        plan = json.loads(PLAN.read_text())
        for record in plan["configs"].values():
            if sha256_file(ROOT / record["path"]) != record["sha256"]:
                raise RuntimeError("frozen WP6 reference configuration hash mismatch")
        return plan
    row = _read_bestfit()
    configs = {
        "public_release_fixed_point": _info(_public_example_params(), "public_release_fixed_point"),
        "official_cpl_map_point": _info(_official_map_params(row), "official_cpl_map_point"),
    }
    config_records = {}
    for name, info in configs.items():
        path = RUN / "configs" / f"{name}.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml_dump(info))
        config_records[name] = {
            "path": str(path.relative_to(ROOT)),
            "sha256": sha256_file(path),
        }
    plan = {
        "schema_version": "wp6-reference-benchmark-plan-v1",
        "status": "FROZEN_BEFORE_REFERENCE_EVALUATION",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "configs": config_records,
        "tests": {
            "public_release_fixed_point": {
                "source": "pinned official test_fs_bao_all.yaml and code comment",
                "expected_chi2_FS_BAO": 1176.98,
                "max_abs_delta_chi2": 0.10,
            },
            "official_cpl_map_point": {
                "source_url": BESTFIT_URL,
                "source_sha256": BESTFIT_SHA256,
                "expected_chi2_FS_BAO": row[
                    "chi2__desi_y1_cosmo_bindings.cobaya_likelihoods.fs_bao_likelihoods.desi_fs_bao_all"
                ],
                "max_abs_delta_chi2": 0.10,
                "role": "cross-implementation posterior-supported MAP point",
            },
        },
        "posterior_sampling_authorized": False,
        "fate_calculation_authorized": False,
    }
    atomic_write_json(PLAN, plan)
    return plan


if __name__ == "__main__":
    print(json.dumps(prepare(), indent=2))
