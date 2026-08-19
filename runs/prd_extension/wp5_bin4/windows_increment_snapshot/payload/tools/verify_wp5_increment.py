#!/usr/bin/env python3
import argparse,hashlib,json
from pathlib import Path
def h(p):
 d=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):d.update(b)
 return d.hexdigest()
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();m=json.loads((a.root/'INCREMENT_MANIFEST.json').read_text());bad=[]
for r in m['files']:
 q=a.root/r['path']
 if not q.is_file() or q.stat().st_size!=r['bytes'] or h(q)!=r['sha256']:bad.append(r['path'])
print(json.dumps({'status':'PASS' if not bad else 'FAIL','checked':len(m['files']),'failures':bad}));raise SystemExit(bool(bad))
