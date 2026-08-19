#!/usr/bin/env python3
import hashlib,json,tarfile
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];source=ROOT/'runs/prd_extension/wp5_bin4/production_system'
for tag in ('0p005','0p01','0p02'):
 p=json.loads((source/f'delta_{tag}/external_monitor/final_stop_audit.json').read_text())
 assert p['post_termination_gates_pass'] is True and p['status'].startswith('EXTERNALLY_STOPPED')
def h(p):
 d=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):d.update(b)
 return d.hexdigest()
files=[{'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':h(p)} for p in sorted(x for x in source.rglob('*') if x.is_file())]
manifest=ROOT/'WP5_BIN4_RESULT_MANIFEST.json';manifest.write_text(json.dumps({'schema_version':'wp5-bin4-return-v1','created_at_utc':datetime.now(timezone.utc).isoformat(),'files':files},indent=2,sort_keys=True)+'\n')
archive=ROOT/'WP5_BIN4_RESULTS.tar.gz'
with tarfile.open(archive,'w:gz') as t:t.add(source,arcname='runs/prd_extension/wp5_bin4/production_system');t.add(manifest,arcname=manifest.name)
checksum=ROOT/'WP5_BIN4_RESULTS.tar.gz.sha256';checksum.write_text(f'{h(archive)}  {archive.name}\n')
print(json.dumps({'archive':str(archive),'bytes':archive.stat().st_size,'sha256':h(archive)}))
