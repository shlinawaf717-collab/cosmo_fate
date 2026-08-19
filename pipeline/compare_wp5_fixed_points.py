#!/usr/bin/env python3
import argparse,json
from pathlib import Path
from pipeline.audit_wp4_f0_reproduction import atomic_write_json
LIMIT=.1
def compare(reference,candidate,output):
 r=json.loads(reference.read_text());c=json.loads(candidate.read_text())
 if r['fixed_point']!=c['fixed_point'] or set(r['component_chi2'])!=set(c['component_chi2']):raise ValueError('WP5 fixed-point identity differs')
 components={}
 for n in sorted(r['component_chi2']):
  d=c['component_chi2'][n]-r['component_chi2'][n];components[n]={'signed_difference':d,'absolute_difference':abs(d),'pass':abs(d)<=LIMIT}
 d=c['total_likelihood_chi2']-r['total_likelihood_chi2'];g={'total':abs(d)<=LIMIT,'components':all(x['pass'] for x in components.values())}
 out={'schema_version':'wp5-bin4-fixed-point-comparison-v1','status':'PASS' if all(g.values()) else 'FAIL','threshold_absolute_chi2':LIMIT,'gates':g,'total_signed_difference':d,'components':components}
 atomic_write_json(output,out);return out
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--reference',type=Path,required=True);p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();o=compare(a.reference,a.candidate,a.output);print(json.dumps({'status':o['status'],'output':str(a.output)}));raise SystemExit(0 if o['status']=='PASS' else 1)
