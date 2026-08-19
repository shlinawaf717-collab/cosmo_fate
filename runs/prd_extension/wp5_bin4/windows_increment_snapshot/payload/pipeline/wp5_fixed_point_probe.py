#!/usr/bin/env python3
"""Evaluate one frozen non-posterior WP5 point for cross-platform drift."""
import argparse,json,os,platform,time
from datetime import datetime,timezone
from pathlib import Path
from cobaya.model import get_model
from cobaya.yaml import yaml_load_file
from pipeline.audit_wp4_f0_reproduction import atomic_write_json

POINT={"logA":3.041,"ns":.9655,"theta_MC_100":1.04086,"ombh2":.02227,"omch2":.11923,"tau":.05405,
       "w1":-1.0,"w2":-.9,"w3":-1.5,"w4":-1.7,"Mb":-19.383,"A_planck":1.0,
       "amp_143":17.0,"amp_217":11.0,"amp_143x217":8.0,"n_143":1.0,"n_217":1.6,"n_143x217":1.9,"calTE":1.0,"calEE":1.0}

def run(config,packages,output):
 info=yaml_load_file(str(config));info.pop('sampler',None);info.pop('output',None);info['packages_path']=str(packages.resolve());info['theory']['pipeline.wp5_camb.BIN4CAMB']['path']='global'
 start=time.monotonic();m=get_model(info)
 try:
  p=m.logposterior(POINT,make_finite=False);names=list(m.likelihood);likes={n:float(v) for n,v in zip(names,p.loglikes)}
 finally:m.close()
 out={"schema_version":"wp5-bin4-fixed-point-v1","created_at_utc":datetime.now(timezone.utc).isoformat(),"purpose":"cross-platform drift screen before WP5 production","environment":{"platform":platform.platform(),"python":platform.python_version()},"config":str(config),"fixed_point":POINT,"loglikes":likes,"component_chi2":{n:-2*v for n,v in likes.items()},"total_likelihood_chi2":-2*sum(likes.values()),"runtime_seconds":time.monotonic()-start,"scientific_role":"implementation diagnostic only"}
 atomic_write_json(output,out);return out

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);p.add_argument('--packages',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();o=run(a.config,a.packages,a.output);print(json.dumps({'output':str(a.output),'chi2':o['total_likelihood_chi2'],'seconds':o['runtime_seconds']}))
