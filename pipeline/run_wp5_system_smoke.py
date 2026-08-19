#!/usr/bin/env python3
"""Test one frozen production config per WP5 width without sampling."""

import json,os,subprocess
from datetime import datetime,timezone
from pathlib import Path

from pipeline.audit_wp4_f0_reproduction import atomic_write_json,sha256_file
from pipeline.evaluate_wp5_external_stop import ROOT,SYSTEM_ROOT,validate
from pipeline.run_wp5_bin4_smoke import audit_log


OUTPUT=SYSTEM_ROOT/"system_smoke_audit.json"


def run():
    validate();plan=json.loads((SYSTEM_ROOT/"run_plan.json").read_text());records=[]
    env=os.environ.copy();env.update({name:"1" for name in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","NUMEXPR_NUM_THREADS","VECLIB_MAXIMUM_THREADS")});env["PYTHONPATH"]=str(ROOT)
    for tag in ("0p005","0p01","0p02"):
        row=next(x for x in plan["chains"] if x["width_tag"]==tag and x["chain"]==1)
        config=ROOT/row["config"];log=config.parent/"system_smoke.log"
        result=subprocess.run([str(ROOT/".venv/bin/cobaya-run"),str(config),"--test","--no-mpi","--force"],cwd=ROOT,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        log.write_text(result.stdout);markers=audit_log(result.stdout);samples=list(config.parent.glob("chain.*.txt"))
        records.append({"width_tag":tag,"config":row["config"],"config_sha256":row["config_sha256"],"returncode":result.returncode,"markers":markers,"sample_files":[str(p.relative_to(ROOT)) for p in samples],"log":str(log.relative_to(ROOT)),"log_sha256":sha256_file(log),"pass":result.returncode==0 and all(markers.values()) and not samples})
    payload={"schema_version":"wp5-bin4-production-system-smoke-v1","status":"PASS" if all(r["pass"] for r in records) else "FAIL","created_at_utc":datetime.now(timezone.utc).isoformat(),"runs":records,"sampling_performed":False,"posterior_generated":False,"fate_calculation_performed":False}
    atomic_write_json(OUTPUT,payload);return payload


if __name__=="__main__":
    payload=run();print(json.dumps({"status":payload["status"],"widths":len(payload["runs"])}));raise SystemExit(0 if payload["status"]=="PASS" else 1)
