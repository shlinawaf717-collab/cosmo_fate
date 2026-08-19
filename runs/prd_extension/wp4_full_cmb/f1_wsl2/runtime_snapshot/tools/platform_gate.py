#!/usr/bin/env python3
import argparse, json, platform
from pathlib import Path

p=argparse.ArgumentParser(); p.add_argument('--output',type=Path,required=True); a=p.parse_args()
release=platform.release().lower(); machine=platform.machine().lower()
gates={'linux':platform.system()=='Linux','x86_64':machine in {'x86_64','amd64'},'wsl2':('microsoft' in release and 'wsl2' in release) or Path('/proc/sys/fs/binfmt_misc/WSLInterop').exists()}
payload={'schema_version':'wp4-f1-wsl2-platform-v1','status':'PASS' if all(gates.values()) else 'FAIL','platform':platform.platform(),'machine':machine,'release':release,'gates':gates}
a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n')
print(json.dumps(payload)); raise SystemExit(0 if payload['status']=='PASS' else 1)
