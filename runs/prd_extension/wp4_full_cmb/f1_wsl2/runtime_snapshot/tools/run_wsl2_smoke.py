#!/usr/bin/env python3
import argparse, json, shutil, subprocess
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[1]; config=ROOT/'payload/pipeline/wp4_f1.yaml'; smoke=ROOT/'work/preflight/f1_smoke'
p=argparse.ArgumentParser(); p.add_argument('--output',type=Path,required=True); a=p.parse_args()
if smoke.exists(): shutil.rmtree(smoke)
info=yaml.safe_load(config.read_text()); info['packages_path']=str((ROOT/'payload/data/cobaya_packages').resolve()); info['theory']['camb']['path']='global'; info['output']=str((smoke/'chain').resolve()); temp=ROOT/'work/preflight/wsl2_smoke.yaml'; temp.write_text(yaml.safe_dump(info,sort_keys=False,width=100))
r=subprocess.run([str(ROOT/'.venv/bin/cobaya-run'),str(temp),'--test','--no-mpi','--force'],cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
(ROOT/'work/preflight/f1_smoke.log').write_text(r.stdout)
updated=smoke/'chain.updated.yaml'; resolved=yaml.safe_load(updated.read_text()) if updated.exists() else {}
markers={'test_success':'Test initialization successful' in r.stdout,'desi':'[bao.desi_dr2.desi_bao_all] Initialized.' in r.stdout,'npipe':'planck_npipe_highl_camspec.ttteee' in r.stdout.lower(),'act':'Loading ACT DR6 lensing likelihood v1.2' in r.stdout,'clik_checks':r.stdout.count('Checking likelihood')==2,'shoes':'sn.pantheonplusshoes' in resolved.get('likelihood',{}),'Mb':'Mb' in r.stdout,'P1':'matter_dom' in r.stdout}
chains=list(smoke.glob('chain.*.txt')); passed=r.returncode==0 and all(markers.values()) and not chains
payload={'schema_version':'wp4-f1-wsl2-smoke-v1','status':'PASS' if passed else 'FAIL','returncode':r.returncode,'sampling_performed':False,'fate_calculation_performed':False,'markers':markers,'chain_files':[str(x) for x in chains]}
a.output.write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n'); print(r.stdout); print(json.dumps(payload)); raise SystemExit(0 if passed else 1)
