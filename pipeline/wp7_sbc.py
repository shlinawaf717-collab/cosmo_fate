#!/usr/bin/env python3
"""Generate and audit the 50 frozen primary-prior WP7 SBC datasets."""

from __future__ import annotations

import argparse
import functools
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from pipeline.bgtheory import C_KMS, MNU_OMH2, OMEGA_R_H2, _ZGRID
from pipeline.cmb_distprior import PlanckDistPrior, predict_R_lA_generic
from pipeline.make_mocks import (
    BAO_DIR,
    SN_DIR,
    load_sn_cov,
    portable_symlink,
    sha256_file,
    sha256_obj,
)
from pipeline.wp7_fs7 import admissibility, draw_truncated_latents, latent_to_nodes, make_ln_fde


ROOT = Path(__file__).resolve().parents[1]
SBC_ROOT = ROOT / "runs/prd_extension/wp7/sbc"
MANIFEST = SBC_ROOT / "sbc_manifest.json"
COUNT = 50
TRUTH_ROOT_SEED = 2026090800
NOISE_ROOT_SEED = 2026090900


class WP7SBCError(RuntimeError):
    pass


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as stream:
        json.dump(payload, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
        temporary = Path(stream.name)
    os.replace(temporary, path)


class FS7MockBackground:
    """The same background equations used by BackgroundW, with a mock API."""

    def __init__(self, truth: dict):
        self.truth = truth
        self.nodes = np.asarray(truth["fs7_nodes"], dtype=float)
        h0, om = float(truth["H0"]), float(truth["omegam"])
        h2 = (h0 / 100.0) ** 2
        omr = OMEGA_R_H2 / h2
        ode = 1.0 - om - omr
        omch2 = om * h2 - float(truth["ombh2"]) - MNU_OMH2
        if ode <= 0 or omch2 <= 0:
            raise WP7SBCError("truth is outside the physical BackgroundW/CAMB domain")
        scale = 1.0 / (1.0 + _ZGRID)
        fde = np.exp(np.clip(make_ln_fde(self.nodes)(scale), -700.0, 700.0))
        e2 = omr * (1.0 + _ZGRID) ** 4 + om * (1.0 + _ZGRID) ** 3 + ode * fde
        if np.any(~np.isfinite(e2)) or np.any(e2 <= 0):
            raise WP7SBCError("truth background is non-finite")
        self.H = h0 * np.sqrt(e2)
        integral = C_KMS / self.H
        self.chi = np.concatenate([
            [0.0],
            np.cumsum(0.5 * (integral[1:] + integral[:-1]) * np.diff(_ZGRID)),
        ])
        import camb

        pars = camb.set_params(
            ombh2=float(truth["ombh2"]), omch2=omch2, H0=h0, mnu=0.06,
            nnu=3.044, num_massive_neutrinos=1, tau=0.054, As=2.1e-9, ns=0.9649,
        )
        self.rdrag = float(camb.get_background(pars).get_derived_params()["rdrag"])

    def angular_diameter_distance(self, z):
        z = np.asarray(z, dtype=float)
        return np.interp(z, _ZGRID, self.chi) / (1.0 + z)

    def hubble_parameter(self, z):
        return np.interp(np.asarray(z, dtype=float), _ZGRID, self.H)

    def get_derived_params(self):
        return {"rdrag": self.rdrag}


@functools.lru_cache(maxsize=1)
def common_assets() -> dict:
    import pandas as pd

    sn_data = Path(SN_DIR) / "Pantheon+SH0ES.dat"
    sn_cov_path = Path(SN_DIR) / "Pantheon+SH0ES_STAT+SYS.cov"
    frame = pd.read_csv(sn_data, sep=r"\s+")
    zcmb = frame["zHD"].to_numpy()
    is_cal = frame["IS_CALIBRATOR"].to_numpy().astype(bool)
    mask = (zcmb > 0.01) | is_cal
    covariance = load_sn_cov()[np.ix_(mask, mask)]

    bao_mean_path = Path(BAO_DIR) / "desi_gaussian_bao_ALL_GCcomb_mean.txt"
    bao_cov_path = Path(BAO_DIR) / "desi_gaussian_bao_ALL_GCcomb_cov.txt"
    bao_rows = []
    for line in bao_mean_path.read_text().splitlines():
        if line.strip() and not line.startswith("#"):
            z, _, quantity = line.split()
            bao_rows.append((float(z), quantity))
    bao_cov = np.loadtxt(bao_cov_path)
    sigma = np.asarray(PlanckDistPrior.sigma, dtype=float)
    corr = np.asarray(PlanckDistPrior.corr, dtype=float)
    cmb_cov = corr * np.outer(sigma, sigma)
    return {
        "sn_df": frame,
        "sn_mask": mask,
        "L_sn": np.linalg.cholesky(covariance),
        "bao_rows_definition": bao_rows,
        "L_bao": np.linalg.cholesky(bao_cov),
        "L_cmb": np.linalg.cholesky(cmb_cov),
        "sn_cov_source": str(sn_cov_path),
        "bao_cov_source": str(bao_cov_path),
        "input_fingerprint": {
            "sn_data_sha256": sha256_file(sn_data),
            "sn_cov_sha256": sha256_file(sn_cov_path),
            "bao_mean_sha256": sha256_file(bao_mean_path),
            "bao_cov_sha256": sha256_file(bao_cov_path),
            "cmb_prior_sha256": sha256_obj({"sigma": sigma.tolist(), "corr": corr.tolist()}),
        },
    }


def draw_truth(index: int) -> tuple[dict, FS7MockBackground]:
    truth_seed = TRUTH_ROOT_SEED + index
    function_seq, scalar_seq = np.random.SeedSequence(truth_seed).spawn(2)
    function_seed = int(function_seq.generate_state(1, dtype=np.uint32)[0])
    scalar_rng = np.random.default_rng(scalar_seq)
    latent, rejection = draw_truncated_latents(1, 0.5, 0.7, seed=function_seed, batch_size=64)
    z = latent[0]
    nodes = latent_to_nodes(z, 0.5, 0.7)
    for attempt in range(1, 10001):
        truth = {
            "schema_version": "wp7-fs7-sbc-truth-v1",
            "dataset_index": index,
            "truth_seed": truth_seed,
            "function_substream_seed": function_seed,
            "scalar_attempt": attempt,
            "ombh2": float(scalar_rng.uniform(0.005, 0.1)),
            "omegam": float(scalar_rng.uniform(0.01, 0.99)),
            "H0": float(scalar_rng.uniform(20.0, 100.0)),
            "Mb": float(scalar_rng.uniform(-20.0, -18.0)),
            "latent_z": z.tolist(),
            "fs7_nodes": nodes.tolist(),
            "function_rejection_audit": rejection,
            "prior": "primary normalized FS7 plus D0 P1 scalar priors conditioned on physical theory domain",
        }
        try:
            background = FS7MockBackground(truth)
        except Exception:
            continue
        return truth, background
    raise WP7SBCError(f"s{index:03d}: failed to draw a physical scalar truth")


def dataset_assets(truth: dict, background: FS7MockBackground) -> dict:
    common = common_assets()
    frame = common["sn_df"]
    zcmb = frame["zHD"].to_numpy()
    zhel = frame["zHEL"].to_numpy()
    is_cal = frame["IS_CALIBRATOR"].to_numpy().astype(bool)
    da = background.angular_diameter_distance(zcmb)
    prediction = 5.0 * np.log10((1.0 + zhel) * (1.0 + zcmb) * da) + truth["Mb"] + 25.0
    prediction[is_cal] = frame["CEPH_DIST"].to_numpy()[is_cal] + truth["Mb"]

    bao_rows = []
    for z, quantity in common["bao_rows_definition"]:
        da_z = float(background.angular_diameter_distance(z))
        hz = float(background.hubble_parameter(z))
        dm, dh = (1.0 + z) * da_z, C_KMS / hz
        if quantity == "DM_over_rs":
            value = dm / background.rdrag
        elif quantity == "DH_over_rs":
            value = dh / background.rdrag
        elif quantity == "DV_over_rs":
            value = (dm * dm * C_KMS * z / hz) ** (1.0 / 3.0) / background.rdrag
        else:
            raise WP7SBCError(f"unknown BAO quantity {quantity}")
        bao_rows.append((z, value, quantity))

    R, lA = predict_R_lA_generic(
        truth["ombh2"], truth["omegam"], truth["H0"], make_ln_fde(truth["fs7_nodes"])
    )
    return {
        "sn_df": frame,
        "sn_mu": prediction,
        "sn_mask": common["sn_mask"],
        "L_sn": common["L_sn"],
        "bao_rows": bao_rows,
        "bao_mu": np.asarray([row[1] for row in bao_rows]),
        "L_bao": common["L_bao"],
        "cmb_mu": np.asarray([R, lA, truth["ombh2"]]),
        "L_cmb": common["L_cmb"],
        "sn_cov_source": common["sn_cov_source"],
        "bao_cov_source": common["bao_cov_source"],
        "input_fingerprint": common["input_fingerprint"],
    }


def write_dataset(directory: Path, truth: dict, assets: dict, noise_seed: int) -> None:
    if directory.exists():
        raise WP7SBCError(f"refusing existing SBC directory {directory}")
    directory.mkdir(parents=True)
    rng = np.random.default_rng(noise_seed)
    frame = assets["sn_df"].copy()
    mock_mag = frame["m_b_corr"].to_numpy().copy()
    mask = assets["sn_mask"]
    mock_mag[mask] = assets["sn_mu"][mask] + assets["L_sn"] @ rng.standard_normal(mask.sum())
    frame["m_b_corr"] = mock_mag
    frame.to_csv(directory / "sn_mock.dat", sep=" ", index=False)
    portable_symlink(assets["sn_cov_source"], directory / "sn_cov.cov")
    (directory / "config.dataset").write_text(
        "name = WP7_FS7_SBC\ndata_file = sn_mock.dat\nmag_covmat_file = sn_cov.cov\n"
    )
    bao = assets["bao_mu"] + assets["L_bao"] @ rng.standard_normal(len(assets["bao_mu"]))
    with (directory / "bao_mean.txt").open("w") as stream:
        stream.write("# [z] [value at z] [quantity]\n")
        for (z, _, quantity), value in zip(assets["bao_rows"], bao):
            stream.write(f"{z:.8f} {value:.8f} {quantity}\n")
    portable_symlink(assets["bao_cov_source"], directory / "bao_cov.txt")
    cmb = assets["cmb_mu"] + assets["L_cmb"] @ rng.standard_normal(3)
    atomic_json(directory / "cmb_mean.json", {"mean": cmb.tolist()})
    atomic_json(directory / "truth.json", truth | {"noise_seed": noise_seed})


def generate() -> dict:
    if SBC_ROOT.exists() and any(SBC_ROOT.iterdir()):
        if MANIFEST.is_file():
            return audit()
        raise WP7SBCError("refusing non-empty unmanifested SBC root")
    SBC_ROOT.mkdir(parents=True, exist_ok=True)
    records = []
    for index in range(1, COUNT + 1):
        truth, background = draw_truth(index)
        directory = SBC_ROOT / f"s{index:03d}"
        write_dataset(directory, truth, dataset_assets(truth, background), NOISE_ROOT_SEED + index)
        records.append({
            "index": index,
            "truth_sha256": sha256_file(directory / "truth.json"),
            "noise_seed": NOISE_ROOT_SEED + index,
        })
    payload = {
        "schema_version": "wp7-fs7-sbc-manifest-v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "FROZEN_INPUTS_BEFORE_SBC_INFERENCE",
        "datasets": COUNT,
        "truth_root_seed": TRUTH_ROOT_SEED,
        "noise_root_seed": NOISE_ROOT_SEED,
        "input_fingerprint": common_assets()["input_fingerprint"],
        "records": records,
        "aggregate_truth_or_fate_endpoint_calculated": False,
    }
    atomic_json(MANIFEST, payload)
    return audit()


def audit() -> dict:
    manifest = json.loads(MANIFEST.read_text())
    failures = []
    for record in manifest["records"]:
        index = record["index"]
        directory = SBC_ROOT / f"s{index:03d}"
        truth_path = directory / "truth.json"
        required = ("sn_mock.dat", "sn_cov.cov", "config.dataset", "bao_mean.txt", "bao_cov.txt", "cmb_mean.json", "truth.json")
        if any(not (directory / name).exists() for name in required):
            failures.append({"index": index, "reason": "missing_input"}); continue
        if sha256_file(truth_path) != record["truth_sha256"]:
            failures.append({"index": index, "reason": "truth_hash"}); continue
        truth = json.loads(truth_path.read_text())
        if not admissibility(truth["fs7_nodes"]).admissible:
            failures.append({"index": index, "reason": "inadmissible_truth"})
        h2 = (truth["H0"] / 100.0) ** 2
        if truth["omegam"] * h2 - truth["ombh2"] - MNU_OMH2 <= 0:
            failures.append({"index": index, "reason": "nonpositive_cdm"})
        for name in ("sn_cov.cov", "bao_cov.txt"):
            link = directory / name
            if not link.is_symlink() or Path(os.readlink(link)).is_absolute() or not link.resolve().is_file():
                failures.append({"index": index, "reason": f"bad_link_{name}"})
    return {
        "schema_version": "wp7-fs7-sbc-input-audit-v1",
        "status": "PASS" if not failures else "FAIL",
        "datasets": len(manifest["records"]),
        "failures": failures,
        "posterior_sampling_performed": False,
        "aggregate_truth_or_fate_endpoint_calculated": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", action="store_true")
    args = parser.parse_args()
    result = audit() if args.audit else generate()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
