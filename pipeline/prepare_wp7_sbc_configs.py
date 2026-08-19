#!/usr/bin/env python3
"""Freeze two-chain inference configs for all 50 WP7 SBC datasets."""

from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path

from cobaya.yaml import yaml_dump, yaml_load_file

from pipeline.audit_wp4_f0_reproduction import atomic_write_json, sha256_file
from pipeline.build_wp7_configs import ROOT
from pipeline.wp7_sbc import COUNT, MANIFEST, SBC_ROOT


BASE = ROOT / "runs/prd_extension/wp7/configs/fs7_primary.yaml"
PLAN = SBC_ROOT / "inference_plan.json"


def prepare() -> dict:
    if PLAN.is_file():
        plan = json.loads(PLAN.read_text())
        for chain in plan["chains"]:
            if sha256_file(ROOT / chain["config"]) != chain["config_sha256"]:
                raise RuntimeError("frozen WP7 SBC config hash mismatch")
        return plan
    manifest = json.loads(MANIFEST.read_text())
    if manifest["status"] != "FROZEN_INPUTS_BEFORE_SBC_INFERENCE" or manifest["datasets"] != COUNT:
        raise RuntimeError("WP7 SBC inputs are not frozen")
    base = yaml_load_file(str(BASE))
    chains = []
    for index in range(1, COUNT + 1):
        dataset = SBC_ROOT / f"s{index:03d}"
        cmb_mean = json.loads((dataset / "cmb_mean.json").read_text())["mean"]
        for chain_index in (1, 2):
            info = copy.deepcopy(base)
            info["packages_path"] = str(ROOT / "data/cobaya_packages")
            info["likelihood"]["sn.pantheonplusshoes"] = {
                "path": str(dataset), "dataset_file": "config.dataset", "use_abs_mag": True,
            }
            info["likelihood"]["bao.desi_dr2.desi_bao_all"] = {
                "path": str(dataset), "measurements_file": "bao_mean.txt",
                "cov_file": "bao_cov.txt", "rs_fid": 1,
            }
            info["likelihood"]["pipeline.cmb_distprior.ProviderDistPrior"]["mean"] = cmb_mean
            seed = 2026100000 + 10 * index + chain_index
            mcmc = info["sampler"]["mcmc"]
            mcmc.update(seed=seed, Rminus1_stop=1.0e-6, Rminus1_cl_stop=1.0e-6, max_samples=float("inf"))
            directory = dataset / f"c{chain_index}"
            directory.mkdir(parents=True, exist_ok=True)
            info["output"] = str(directory / "chain")
            info["wp7_metadata"] = {
                "role": "WP7 primary-prior SBC posterior; no real-data endpoint",
                "dataset_index": index,
                "chain_index": chain_index,
            }
            config = directory / "run.yaml"
            config.write_text(yaml_dump(info), encoding="utf-8")
            chains.append({
                "dataset_index": index, "chain_index": chain_index, "seed": seed,
                "config": str(config.relative_to(ROOT)), "config_sha256": sha256_file(config),
                "output_prefix": str((directory / "chain").relative_to(ROOT)),
            })
    plan = {
        "schema_version": "wp7-fs7-sbc-inference-plan-v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "FROZEN_BEFORE_SBC_POSTERIOR_SAMPLING",
        "datasets": COUNT,
        "chains_per_dataset": 2,
        "max_parallel_chains": 6,
        "base_config": {"path": str(BASE.relative_to(ROOT)), "sha256": sha256_file(BASE)},
        "input_manifest": {"path": str(MANIFEST.relative_to(ROOT)), "sha256": sha256_file(MANIFEST)},
        "chains": chains,
        "real_data_endpoint_read": False,
        "sbc_rank_calculated": False,
    }
    atomic_write_json(PLAN, plan)
    return plan


if __name__ == "__main__":
    print(json.dumps({"status": prepare()["status"], "plan": str(PLAN)}, sort_keys=True))
