#!/usr/bin/env python3
import argparse, json
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; pre=ROOT/'work/preflight'
FILES=['platform.json','package_integrity.json','environment.json','input_integrity.json','camb_comparison.json','f1_fixed_point_comparison.json','f1_smoke_test.json','activation_verification.json']
p=argparse.ArgumentParser(); p.add_argument('--output',type=Path,required=True); p.add_argument('--require-pass',action='store_true'); a=p.parse_args()
records={}; missing=[]
for name in FILES:
 path=pre/name
 if not path.exists(): missing.append(name)
 else: records[name]=json.loads(path.read_text()).get('status')
passed=not missing and all(value=='PASS' for value in records.values())
payload={'schema_version':'wp4-f1-wsl2-aggregate-preflight-v1','created_at_utc':datetime.now(timezone.utc).isoformat(),'status':'PASS' if passed else 'FAIL','records':records,'missing':missing,'production_authorized':passed,'mac_samples_included':False}
a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n'); print(json.dumps(payload,indent=2)); raise SystemExit(0 if passed or not a.require_pass else 1)
