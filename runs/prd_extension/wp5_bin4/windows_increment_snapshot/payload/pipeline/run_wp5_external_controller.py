#!/usr/bin/env python3
"""Periodically evaluate and finalize one WP5 smoothing width."""

import argparse,json,os,subprocess,sys,time
from datetime import datetime,timezone

from pipeline.evaluate_wp5_external_stop import SYSTEM_ROOT,evaluate
from pipeline.monitor_wp5_bin4 import WIDTH_TAGS


def append(path,event):
    path.parent.mkdir(parents=True,exist_ok=True);payload={**event,"timestamp_utc":datetime.now(timezone.utc).isoformat()}
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_APPEND,0o644)
    try:os.write(fd,(json.dumps(payload,sort_keys=True)+"\n").encode());os.fsync(fd)
    finally:os.close(fd)


def run(width_tag,interval):
    state=SYSTEM_ROOT/f"delta_{width_tag}/external_monitor";events=state/"controller_events.jsonl"
    append(events,{"event":"controller_start","pid":os.getpid(),"width_tag":width_tag})
    while True:
        try:payload=evaluate(width_tag)
        except (FileNotFoundError,ValueError) as exc:
            append(events,{"event":"chains_not_ready","error":f"{type(exc).__name__}: {exc}"});time.sleep(interval);continue
        append(events,{"event":"evaluation","status":payload["status"],"snapshot_sha256":payload["snapshot_sha256"]})
        if payload["stop_eligible"]:
            r=subprocess.run([sys.executable,str(SYSTEM_ROOT.parents[3]/"pipeline/finalize_wp5_external_stop.py"),width_tag],capture_output=True,text=True)
            append(events,{"event":"finalizer_exit","returncode":r.returncode,"stdout":r.stdout.strip(),"stderr":r.stderr.strip()});return r.returncode
        time.sleep(interval)


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("width_tag",choices=WIDTH_TAGS);p.add_argument("--interval-seconds",type=float,default=1800);a=p.parse_args();raise SystemExit(run(a.width_tag,a.interval_seconds))
