#!/usr/bin/env python3
import argparse, hashlib, json
from pathlib import Path

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()
p=argparse.ArgumentParser(); p.add_argument('--root',type=Path,required=True); a=p.parse_args()
m=json.loads((a.root/'INCREMENT_MANIFEST.json').read_text()); failures=[]
for r in m['files']:
    path=a.root/r['path']
    if not path.is_file() or path.stat().st_size!=r['bytes'] or sha(path)!=r['sha256']:
        failures.append(r['path'])
print(json.dumps({'status':'PASS' if not failures else 'FAIL','checked':len(m['files']),'failures':failures}))
raise SystemExit(0 if not failures else 1)
