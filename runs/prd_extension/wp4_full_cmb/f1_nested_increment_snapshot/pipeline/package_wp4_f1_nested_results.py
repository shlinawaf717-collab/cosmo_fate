#!/usr/bin/env python3
import hashlib,json,tarfile
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]; source=ROOT/'work/f1_nested'
completion=json.loads((source/'completion.json').read_text())
if completion.get('status')!='PASS' or completion.get('completed_runs')!=12 or not (source/'nested_endpoints.json').is_file():
    raise RuntimeError('nested campaign/endpoints are incomplete')
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()
files=[]
for p in sorted(x for x in source.rglob('*') if x.is_file()):
    files.append({'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':sha(p)})
manifest=ROOT/'WP4_F1_NESTED_RESULT_MANIFEST.json'
manifest.write_text(json.dumps({'schema_version':'wp4-f1-nested-return-v1','created_at_utc':datetime.now(timezone.utc).isoformat(),'files':files},indent=2,sort_keys=True)+'\n')
archive=ROOT/'WP4_F1_NESTED_RESULTS.tar.gz'
with tarfile.open(archive,'w:gz') as tar:
    tar.add(source,arcname='work/f1_nested'); tar.add(manifest,arcname=manifest.name)
checksum=ROOT/'WP4_F1_NESTED_RESULTS.tar.gz.sha256'; checksum.write_text(f'{sha(archive)}  {archive.name}\n')
print(json.dumps({'archive':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive)}))
