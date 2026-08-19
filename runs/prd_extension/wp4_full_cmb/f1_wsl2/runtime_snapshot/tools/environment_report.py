#!/usr/bin/env python3
import argparse, importlib.metadata, json, platform, sys
from pathlib import Path

p=argparse.ArgumentParser(); p.add_argument('--output',type=Path,required=True); a=p.parse_args()
expected={'act-dr6-lenslike':'1.2.1','camb':'1.6.6','clipy-like':'0.15','cobaya':'3.6.2','numpy':'2.5.0','scipy':'1.16.2'}
actual={name:importlib.metadata.version(name) for name in expected}; gates={name:actual[name]==version for name,version in expected.items()}
payload={'schema_version':'wp4-f1-wsl2-environment-v1','status':'PASS' if all(gates.values()) and sys.version_info[:2]==(3,13) else 'FAIL','python':platform.python_version(),'platform':platform.platform(),'expected':expected,'actual':actual,'gates':gates,'python_3_13':sys.version_info[:2]==(3,13)}
a.output.write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n'); print(json.dumps(payload)); raise SystemExit(0 if payload['status']=='PASS' else 1)
