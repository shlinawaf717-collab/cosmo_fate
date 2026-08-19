#!/usr/bin/env python3
"""Build the WP6 DR1 FS+BAO replacement configuration without sampling."""

import json
import sys
from datetime import datetime,timezone
from pathlib import Path
from cobaya.yaml import yaml_dump,yaml_load_file

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from pipeline.audit_wp4_f0_reproduction import atomic_write_json,sha256_file

BASE=ROOT/'pipeline/wp4_f1.yaml';DECISION=ROOT/'plan/growth_data_decision.json';AUDIT=ROOT/'runs/prd_extension/wp6_growth/data_audit.json'
CODE=ROOT/'data/wp6_desi_dr1/code/official_likelihood/dr1/cobaya';DATA=ROOT/'data/wp6_desi_dr1/likelihood'
OUTPUT=ROOT/'runs/prd_extension/wp6_growth/config/wp6_cpl_dr1_fs_bao.yaml';PLAN=ROOT/'runs/prd_extension/wp6_growth/config_plan.json'

def build():
 d=json.loads(DECISION.read_text())
 if d['decision']!='GO_FOR_STAGED_IMPLEMENTATION_WITH_DR1_FS_BAO_REPLACEMENT':raise RuntimeError('WP6 data gate is not Go')
 info=yaml_load_file(str(BASE));info['packages_path']=str(ROOT/'data/cobaya_packages')
 info['theory']['pipeline.wp6_desi_fs.DESIDR1ReptVelocileptors']={'python_path':str(ROOT),'is_physical_prior':True,'stop_at_error':True}
 if 'bao.desi_dr2.desi_bao_all' not in info['likelihood']:raise RuntimeError('DR2 BAO missing before replacement')
 likelihood={}
 for name,settings in info['likelihood'].items():
  if name!='bao.desi_dr2.desi_bao_all':likelihood[name]=settings
 likelihood['pipeline.wp6_desi_fs.DESIDR1FSBAO']={'python_path':str(ROOT),'data_dir':str(DATA),'observable_name':'spectrum-poles-rotated+bao-recon','tracers':['bgs_z0','lrg_z0','lrg_z1','lrg_z2','elg_z1','qso_z0','lya_z0'],'solve':'marg','stop_at_error':True}
 info['likelihood']=likelihood
 official_defaults=yaml_load_file(str(CODE/'desi_fs_bao_all.yaml'))
 for name,definition in official_defaults['params'].items():
  if name in info['params']:raise RuntimeError(f'WP6 nuisance parameter collision: {name}')
  info['params'][name]=definition
 # The inherited aggregate chi2__BAO referred to the removed DR2 BAO block.
 # Name the joint replacement honestly: it contains both full shape and DR1 BAO.
 info['params'].pop('chi2__BAO',None)
 info['params']['chi2__FS_BAO']={'latex':r'\chi^2_\mathrm{FS+BAO}','derived':True}
 m=info['sampler']['mcmc'];m['covmat']=None;m.pop('blocking',None);m['measure_speeds']=True;m['seed']=2026082701
 info['output']=str(ROOT/'runs/prd_extension/wp6_growth/smoke/chain')
 return info

def prepare():
 if PLAN.exists():
  p=json.loads(PLAN.read_text());assert sha256_file(ROOT/p['config'])==p['config_sha256'];return p
 OUTPUT.parent.mkdir(parents=True,exist_ok=True);OUTPUT.write_text(yaml_dump(build()))
 data=json.loads(AUDIT.read_text());files=[]
 for r in data['selected_files']:
  p=DATA/r['name'];files.append({'path':str(p.relative_to(ROOT)),'sha256':sha256_file(p),'expected_sha256':r['sha256'],'bytes':p.stat().st_size})
 p={'schema_version':'wp6-growth-config-plan-v1','status':'FROZEN_BEFORE_WP6_LIKELIHOOD_INITIALIZATION','created_at_utc':datetime.now(timezone.utc).isoformat(),'config':str(OUTPUT.relative_to(ROOT)),'config_sha256':sha256_file(OUTPUT),'decision_sha256':sha256_file(DECISION),'data_audit_sha256':sha256_file(AUDIT),'official_code_commit':'7d51f4f86dc3bee6bf10f1a684913c943a89a844','replacement':{'DR2_BAO_present':False,'DR1_FS_BAO_present':True},'selected_files':files,'sampling_performed':False,'fate_calculation_performed':False}
 if not all(r['sha256']==r['expected_sha256'] for r in files):raise RuntimeError('WP6 input hash mismatch')
 atomic_write_json(PLAN,p);return p
if __name__=='__main__':print(json.dumps({'status':prepare()['status'],'config':str(OUTPUT)}))
