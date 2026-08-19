#!/usr/bin/env python3
"""Transactionally stop one converged WP5 width without touching the others."""

from __future__ import annotations

import fcntl
import json
import os
import signal
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from pipeline.evaluate_wp5_external_stop import POLICY, ROOT, SYSTEM_ROOT, gates, load, sha, validate
from pipeline.monitor_wp5_bin4 import WIDTH_TAGS, chain_paths, collect


def atomic(path:Path,payload:dict)->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile("w",encoding="utf-8",dir=path.parent,delete=False) as h:
        json.dump(payload,h,indent=2,sort_keys=True);h.write("\n");h.flush();os.fsync(h.fileno());tmp=Path(h.name)
    os.replace(tmp,path)


def table():
    r=subprocess.run(["ps","-axo","pid=,ppid=,state=,command="],capture_output=True,text=True,check=True)
    rows=[]
    for line in r.stdout.splitlines():
        p=line.strip().split(None,3)
        if len(p)==4: rows.append({"pid":int(p[0]),"ppid":int(p[1]),"state":p[2],"command":p[3]})
    return rows


def discover(width_tag:str):
    driver_pid=int((SYSTEM_ROOT/"driver.lock").read_text().strip()); rows=table()
    driver={r["pid"]:r for r in rows}.get(driver_pid)
    if not driver or "run_wp5_bin4.py" not in driver["command"]: raise RuntimeError("WP5 driver not alive")
    children=[r for r in rows if r["ppid"]==driver_pid and "cobaya-run" in r["command"] and f"delta_{width_tag}" in r["command"] and "--no-mpi" in r["command"]]
    if len(children)!=4: raise RuntimeError(f"expected four {width_tag} children, got {len(children)}")
    for i in range(1,5):
        if sum(f"/c{i}/run.yaml" in r["command"] for r in children)!=1: raise RuntimeError(f"child mapping failed c{i}")
    return driver,sorted(children,key=lambda r:r["command"])


def alive(pid):
    try: os.kill(pid,0);return True
    except ProcessLookupError:return False


def wait_state(pids,prefix,seconds):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        states=[subprocess.run(["ps","-o","state=","-p",str(p)],capture_output=True,text=True).stdout.strip() for p in pids]
        if all(s.startswith(prefix) for s in states): return
        time.sleep(.1)
    raise RuntimeError(f"processes did not reach state {prefix}")


def wait_exit(pids,seconds):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        pids=[p for p in pids if alive(p)]
        if not pids:return []
        time.sleep(.2)
    return pids


def finalize(width_tag:str)->dict:
    if width_tag not in WIDTH_TAGS: raise ValueError(width_tag)
    policy,activation=validate(); state_dir=SYSTEM_ROOT/f"delta_{width_tag}/external_monitor"
    eligibility=state_dir/"stop_eligible.json"
    if not eligibility.exists(): raise RuntimeError("no stop eligibility")
    if load(eligibility)["policy_sha256"]!=sha(POLICY): raise RuntimeError("eligibility policy mismatch")
    stopped=[];committed=False
    with (state_dir/"finalizer.lock").open("w") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        driver,children=discover(width_tag);pids=[r["pid"] for r in children]
        try:
            for pid in pids: os.kill(pid,signal.SIGSTOP);stopped.append(pid)
            wait_state(pids,"T",10)
            paths=list(chain_paths(width_tag,SYSTEM_ROOT));sizes=[p.stat().st_size for p in paths];time.sleep(2)
            if sizes!=[p.stat().st_size for p in paths]: raise RuntimeError("chain sizes changed while paused")
            diagnostics=collect(paths); final_gates=gates(diagnostics,policy)
            if not all(final_gates.values()): raise RuntimeError("paused snapshot failed")
            audit={"schema_version":"wp5-bin4-final-stop-audit-v1","created_at_utc":datetime.now(timezone.utc).isoformat(),
                   "status":"COMMIT_TO_EXTERNAL_STOP","width_tag":width_tag,"policy_sha256":sha(POLICY),
                   "activation_sha256":sha(SYSTEM_ROOT/"activation.json"),"eligibility_sha256":sha(eligibility),
                   "driver":driver,"children":children,"stable_sizes":sizes,"final_diagnostics":diagnostics,
                   "final_policy_gates":final_gates,"checkpoints_edited":False}
            audit_path=state_dir/"final_stop_audit.json";atomic(audit_path,audit);committed=True
            for pid in pids: os.kill(pid,signal.SIGTERM)
            for pid in pids:
                if alive(pid):os.kill(pid,signal.SIGCONT)
            remaining=wait_exit(pids,20);escalated=list(remaining)
            for pid in remaining:os.kill(pid,signal.SIGKILL)
            remaining=wait_exit(remaining,5)
            post=collect(paths);post_gates=gates(post,policy)
            audit.update({"completed_at_utc":datetime.now(timezone.utc).isoformat(),
                          "status":"EXTERNALLY_STOPPED" if not remaining else "EXTERNALLY_STOPPED_WITH_EXIT_WARNING",
                          "children_requiring_sigkill":escalated,"children_still_alive_after_sigkill":remaining,
                          "post_termination_diagnostics":post,"post_termination_policy_gates":post_gates,
                          "post_termination_gates_pass":all(post_gates.values())})
            atomic(audit_path,audit);print(json.dumps({"status":audit["status"],"width_tag":width_tag}));return audit
        except Exception as exc:
            if not committed:
                for pid in stopped:
                    if alive(pid):os.kill(pid,signal.SIGCONT)
                atomic(state_dir/"final_stop_audit.json",{"status":"ABORTED_RESUMED","width_tag":width_tag,"error":f"{type(exc).__name__}: {exc}","checkpoints_edited":False})
            raise


if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("width_tag",choices=WIDTH_TAGS);a=p.parse_args();finalize(a.width_tag)
