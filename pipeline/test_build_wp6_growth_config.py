from pipeline.build_wp6_growth_config import build
def test_wp6_config_replaces_dr2_bao_with_dr1_fs_bao():
 x=build();assert 'bao.desi_dr2.desi_bao_all' not in x['likelihood'];assert 'pipeline.wp6_desi_fs.DESIDR1FSBAO' in x['likelihood'];assert 'pipeline.wp6_desi_fs.DESIDR1ReptVelocileptors' in x['theory'];assert x['likelihood']['pipeline.wp6_desi_fs.DESIDR1FSBAO']['solve']=='marg'
 assert 'pre_BGS_z0.b1p' in x['params'];assert x['params']['pre_BGS_z0.b3p']==0.0
 assert 'chi2__BAO' not in x['params'];assert x['params']['chi2__FS_BAO']['derived'] is True
