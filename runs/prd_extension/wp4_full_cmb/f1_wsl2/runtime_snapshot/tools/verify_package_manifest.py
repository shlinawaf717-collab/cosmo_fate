#!/usr/bin/env python3
import argparse, hashlib, json
from pathlib import Path

def sha(path):
 d=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''): d.update(b)
 return d.hexdigest()
p=argparse.ArgumentParser(); p.add_argument('--root',type=Path,required=True); p.add_argument('--manifest',type=Path,required=True); p.add_argument('--output',type=Path,required=True); a=p.parse_args()
m=json.loads(a.manifest.read_text()); failures=[]
for r in m['files']:
 path=a.root/r['path']
 if not path.is_file(): failures.append({'path':r['path'],'error':'missing'}); continue
 if path.stat().st_size!=r['bytes'] or sha(path)!=r['sha256']: failures.append({'path':r['path'],'error':'mismatch'})
payload={'schema_version':'wp4-f1-taskpack-integrity-v1','status':'PASS' if not failures else 'FAIL','checked_files':len(m['files'])-len(failures),'failures':failures}
a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n'); print(json.dumps({'status':payload['status'],'failures':len(failures)})); raise SystemExit(0 if not failures else 1)
