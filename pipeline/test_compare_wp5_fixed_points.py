import json
from pathlib import Path
from pipeline.compare_wp5_fixed_points import compare
def test_wp5_fixed_point_self_comparison(tmp_path:Path):
 p=tmp_path/'p.json';p.write_text(json.dumps({'fixed_point':{'x':1},'component_chi2':{'a':2},'total_likelihood_chi2':2}));o=compare(p,p,tmp_path/'o.json');assert o['status']=='PASS'
