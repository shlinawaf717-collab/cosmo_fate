#!/usr/bin/env python3
"""Materialize and hash the complete WP5 12-chain production system."""

from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path

from cobaya.yaml import yaml_dump, yaml_load_file

from pipeline.audit_wp4_f0_reproduction import atomic_write_json, sha256_file


ROOT=Path(__file__).resolve().parents[1]
SYSTEM=ROOT/"runs/prd_extension/wp5_bin4/production_system"
PLAN=SYSTEM/"run_plan.json";ACTIVATION=SYSTEM/"activation.json"
POLICY=ROOT/"plan/wp5_external_convergence_policy.json"
PROPOSAL=ROOT/"runs/prd_extension/wp5_bin4/proposal.covmat"
CONFIG_PLAN=ROOT/"runs/prd_extension/wp5_bin4/config_plan.json"
WIDTHS={"0p005":[2026082511,2026082512,2026082513,2026082514],
        "0p01":[2026082521,2026082522,2026082523,2026082524],
        "0p02":[2026082531,2026082532,2026082533,2026082534]}
DELTA={"0p005":.005,"0p01":.01,"0p02":.02}


class WP5FreezeError(RuntimeError):pass


def record(path):return {"path":str(path.relative_to(ROOT)),"sha256":sha256_file(path)}


def prepare():
    if list(SYSTEM.glob("delta_*/c*/chain.*.txt")):
        raise WP5FreezeError("cannot freeze after WP5 production samples exist")
    if PLAN.exists():
        plan=json.loads(PLAN.read_text())
        for chain in plan["chains"]:
            if sha256_file(ROOT/chain["config"])!=chain["config_sha256"]:raise WP5FreezeError("frozen run config changed")
        return plan
    source_plan=json.loads(CONFIG_PLAN.read_text());source={row["delta_lna"]:ROOT/row["path"] for row in source_plan["configs"]}
    chains=[]
    for tag,seeds in WIDTHS.items():
        base=yaml_load_file(str(source[DELTA[tag]]))
        for ordinal,seed in enumerate(seeds,1):
            info=copy.deepcopy(base);directory=SYSTEM/f"delta_{tag}/c{ordinal}";directory.mkdir(parents=True,exist_ok=True)
            info["packages_path"]=str(ROOT/"data/cobaya_packages")
            info["theory"]["pipeline.wp5_camb.BIN4CAMB"]["path"]="global"
            sampler=info["sampler"]["mcmc"];sampler["covmat"]=str(PROPOSAL);sampler["seed"]=seed
            sampler["Rminus1_stop"]=1e-6;sampler["Rminus1_cl_stop"]=1e-6
            info["output"]=str(directory/"chain")
            config=directory/"run.yaml";config.write_text(yaml_dump(info),encoding="utf-8")
            chains.append({"width_tag":tag,"delta_lna":DELTA[tag],"chain":ordinal,"seed":seed,
                           "config":str(config.relative_to(ROOT)),"config_sha256":sha256_file(config),
                           "output_prefix":str((directory/"chain").relative_to(ROOT))})
    plan={"schema_version":"wp5-bin4-run-plan-v1","status":"FROZEN_BEFORE_WP5_PRODUCTION",
          "created_at_utc":datetime.now(timezone.utc).isoformat(),"max_parallel_chains":8,
          "chains_per_width":4,"threads_per_chain":1,"width_order":["0p005","0p01","0p02"],
          "chains":chains,"policy":record(POLICY),"proposal":record(PROPOSAL),
          "config_plan":record(CONFIG_PLAN),"sampling_endpoint_inspection_during_run":False,
          "fate_calculation_during_sampling":False}
    atomic_write_json(PLAN,plan);return plan


def activate():
    plan=prepare()
    runtime={"monitor":ROOT/"pipeline/monitor_wp5_bin4.py",
             "evaluator":ROOT/"pipeline/evaluate_wp5_external_stop.py",
             "finalizer":ROOT/"pipeline/finalize_wp5_external_stop.py",
             "controller":ROOT/"pipeline/run_wp5_external_controller.py",
             "driver":ROOT/"pipeline/run_wp5_bin4.py",
             "freezer":Path(__file__).resolve()}
    inputs={"policy":POLICY,"proposal":PROPOSAL,"config_plan":CONFIG_PLAN,
            "formal_theory_gate":ROOT/"runs/prd_extension/wp5_bin4/formal_theory_gate.json",
            "smoke_audit":ROOT/"runs/prd_extension/wp5_bin4/smoke_audit.json",
            "amendment":ROOT/"plan/wp5_smooth_background_amendment_a013.json",
            "theta_order_correction":ROOT/"plan/wp5_theta_order_correction_a017.json",
            "theta_order_correction_audit":ROOT/"runs/prd_extension/wp5_bin4/theta_order_correction_audit.json",
            "bin4_table":ROOT/"pipeline/wp5_bin4.py","bin4_camb":ROOT/"pipeline/wp5_camb.py",
            "early_de_gate":ROOT/"pipeline/early_de_gate.py"}
    system_smoke=SYSTEM/"system_smoke_audit.json"
    if system_smoke.exists(): inputs["system_smoke_audit"]=system_smoke
    activation={"schema_version":"wp5-bin4-activation-v1","status":"ACTIVE_BEFORE_WP5_PRODUCTION",
                "created_at_utc":datetime.now(timezone.utc).isoformat(),"run_plan_sha256":sha256_file(PLAN),
                "policy_sha256":sha256_file(POLICY),"runtime_hashes":{k:record(v) for k,v in runtime.items()},
                "input_hashes":{k:record(v) for k,v in inputs.items()},
                "config_hashes":{f"{c['width_tag']}_c{c['chain']}":c["config_sha256"] for c in plan["chains"]},
                "WP5_production_samples_exist":False,"scientific_endpoints_inspected":False}
    atomic_write_json(ACTIVATION,activation);return activation


if __name__=="__main__":
    activation=activate();print(json.dumps({"status":activation["status"],"configs":len(activation["config_hashes"])}))
