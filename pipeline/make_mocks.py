"""Gate-2 mock generator (frozen plan §7.4).

Truth = LCDM best fit on D0 (runs/gate2/truth_lcdm_d0.json).
For each mock: draw SN / BAO / CMB-prior data from the exact covariances used
by the likelihoods, around the truth predictions computed with the same code
paths (camb background; predict_R_lA for the CMB prior).

Usage: .venv/bin/python pipeline/make_mocks.py [n_mocks=100] [seed=42]
Mock 000 is always generated with ZERO noise (pipeline validation: chi2~0 at truth).
"""

import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

DATA = os.path.join(ROOT, 'data/cobaya_packages/data')
SN_DIR = os.path.join(DATA, 'sn_data/PantheonPlus')
BAO_DIR = os.path.join(DATA, 'bao_data/desi_bao_dr2')
OUT = os.path.join(ROOT, 'runs/gate2/mocks')
C_KMS = 299792.458
GENERATOR_VERSION = 'make_mocks.v2.append-safe-core'


def truth_background(t):
    import camb
    pars = camb.set_params(ombh2=t['ombh2'], omch2=t['omch2'], H0=t['H0'],
                           mnu=0.06, nnu=3.044, num_massive_neutrinos=1,
                           tau=0.054, As=2.1e-9, ns=0.9649)
    return camb.get_background(pars)


def sn_pred(bg, t):
    """truth m_b_corr prediction for every row of the Pantheon+SH0ES table."""
    import pandas as pd
    df = pd.read_csv(os.path.join(SN_DIR, 'Pantheon+SH0ES.dat'), sep=r'\s+')
    zcmb, zhel = df['zHD'].values, df['zHEL'].values
    is_cal = df['IS_CALIBRATOR'].values.astype(bool)
    ceph = df['CEPH_DIST'].values
    da = bg.angular_diameter_distance(zcmb)
    lum = 5 * np.log10((1 + zhel) * (1 + zcmb) * da)
    pred = lum + t['Mb'] + 25.0
    pred[is_cal] = ceph[is_cal] + t['Mb']
    mask = (zcmb > 0.01) | is_cal
    return df, pred, mask


def load_sn_cov():
    v = np.loadtxt(os.path.join(SN_DIR, 'Pantheon+SH0ES_STAT+SYS.cov'), skiprows=1)
    n = int(np.sqrt(v.size))
    return v.reshape(n, n)


def bao_pred(bg):
    rows = []
    with open(os.path.join(BAO_DIR, 'desi_gaussian_bao_ALL_GCcomb_mean.txt')) as f:
        for line in f:
            if line.strip() and not line.startswith('#'):
                z, _, q = line.split()
                rows.append((float(z), q))
    rd = bg.get_derived_params()['rdrag']
    out = []
    for z, q in rows:
        da = bg.angular_diameter_distance(z)
        hz = bg.hubble_parameter(z)  # km/s/Mpc
        dm = (1 + z) * da
        dh = C_KMS / hz
        if q == 'DM_over_rs':
            out.append((z, dm / rd, q))
        elif q == 'DH_over_rs':
            out.append((z, dh / rd, q))
        elif q == 'DV_over_rs':
            dv = (dm * dm * C_KMS * z / hz) ** (1.0 / 3.0)
            out.append((z, dv / rd, q))
        else:
            raise ValueError(q)
    return out


def canonical_json_bytes(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':')).encode()


def sha256_obj(obj):
    return hashlib.sha256(canonical_json_bytes(obj)).hexdigest()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def build_manifest(truth, seed, n_mocks, cmb_truth_pred, input_fingerprint=None,
                   previous_n=None, append_range=None):
    manifest = {"truth": truth, "seed": seed, "n": n_mocks,
                "cmb_truth_pred": list(cmb_truth_pred),
                "generator_version": GENERATOR_VERSION,
                "truth_fingerprint": sha256_obj(truth)}
    if input_fingerprint is not None:
        manifest["input_fingerprint"] = input_fingerprint
    if previous_n is not None:
        manifest["previous_n"] = previous_n
    if append_range is not None:
        manifest["append_range"] = list(append_range)
    return manifest


def write_mock_dir(d, k, rng, assets):
    """Write one deterministic mock directory using the legacy seed=42 RNG stream."""
    os.makedirs(d, exist_ok=False)
    noise = 0.0 if k == 0 else 1.0

    df = assets['sn_df']
    sn_mu = assets['sn_mu']
    sn_mask = assets['sn_mask']
    mock_mag = df['m_b_corr'].values.copy()
    mock_mag[sn_mask] = sn_mu[sn_mask] + noise * (assets['L_sn'] @ rng.standard_normal(sn_mask.sum()))
    dfm = df.copy()
    dfm['m_b_corr'] = mock_mag
    dfm.to_csv(os.path.join(d, 'sn_mock.dat'), sep=' ', index=False)
    if assets.get('sn_cov_source'):
        os.symlink(assets['sn_cov_source'], os.path.join(d, 'sn_cov.cov'))
    with open(os.path.join(d, 'config.dataset'), 'w') as f:
        f.write("name = PANTHEONPLUS_MOCK\ndata_file = sn_mock.dat\n"
                "mag_covmat_file = sn_cov.cov\n")

    vals = assets['bao_mu'] + noise * (assets['L_bao'] @ rng.standard_normal(len(assets['bao_mu'])))
    with open(os.path.join(d, 'bao_mean.txt'), 'w') as f:
        f.write("# [z] [value at z] [quantity]\n")
        for (z, _, q), v in zip(assets['bao_rows'], vals):
            f.write(f"{z:.8f} {v:.8f} {q}\n")
    if assets.get('bao_cov_source'):
        os.symlink(assets['bao_cov_source'], os.path.join(d, 'bao_cov.txt'))

    cmb = assets['cmb_mu'] + noise * (assets['L_cmb'] @ rng.standard_normal(3))
    with open(os.path.join(d, 'cmb_mean.json'), 'w') as f:
        json.dump({"mean": cmb.tolist()}, f)


def advance_rng_to_index(rng, start_k, assets):
    """Replay legacy draws for mocks 0..start_k-1; O(start_k) by design."""
    for _ in range(start_k):
        rng.standard_normal(assets['sn_mask'].sum())
        rng.standard_normal(len(assets['bao_mu']))
        rng.standard_normal(3)


def production_assets(truth):
    from pipeline.cmb_distprior import predict_R_lA, PlanckDistPrior
    bg = truth_background(truth)
    df, sn_mu, sn_mask = sn_pred(bg, truth)
    sn_cov = load_sn_cov()
    Csub = sn_cov[np.ix_(sn_mask, sn_mask)]
    bao_rows = bao_pred(bg)
    bao_mu = np.array([v for _, v, _ in bao_rows])
    bao_cov_path = os.path.join(BAO_DIR, 'desi_gaussian_bao_ALL_GCcomb_cov.txt')
    bao_cov = np.loadtxt(bao_cov_path)
    R, lA = predict_R_lA(truth['ombh2'], truth['omegam'], truth['H0'], -1.0, 0.0)
    cmb_mu = np.array([R, lA, truth['ombh2']])
    sig = np.asarray(PlanckDistPrior.sigma, float)
    cmb_cov = np.asarray(PlanckDistPrior.corr, float) * np.outer(sig, sig)
    return {'sn_df': df, 'sn_mu': sn_mu, 'sn_mask': sn_mask,
            'L_sn': np.linalg.cholesky(Csub),
            'bao_rows': bao_rows, 'bao_mu': bao_mu,
            'L_bao': np.linalg.cholesky(bao_cov),
            'cmb_mu': cmb_mu, 'L_cmb': np.linalg.cholesky(cmb_cov),
            'sn_cov_source': os.path.join(SN_DIR, 'Pantheon+SH0ES_STAT+SYS.cov'),
            'bao_cov_source': bao_cov_path,
            'input_fingerprint': {
                'sn_cov_sha256': sha256_file(os.path.join(SN_DIR, 'Pantheon+SH0ES_STAT+SYS.cov')),
                'bao_cov_sha256': sha256_file(bao_cov_path),
                'bao_mean_sha256': sha256_file(os.path.join(BAO_DIR, 'desi_gaussian_bao_ALL_GCcomb_mean.txt'))}}


def main(n_mocks=100, seed=42):
    t = json.load(open(os.path.join(ROOT, 'runs/gate2/truth_lcdm_d0.json')))
    assets = production_assets(t)
    print(f"SN: {assets['sn_mask'].sum()} used rows of {len(assets['sn_mu'])}")
    print("CMB truth pred:", assets['cmb_mu'])
    rng = np.random.default_rng(seed)
    os.makedirs(OUT, exist_ok=True)
    for k in range(n_mocks + 1):
        d = os.path.join(OUT, f'm{k:03d}')
        if os.path.exists(d):
            import shutil
            shutil.rmtree(d)
        write_mock_dir(d, k, rng, assets)
    manifest = build_manifest(t, seed, n_mocks, assets['cmb_mu'].tolist(), assets['input_fingerprint'])
    with open(os.path.join(OUT, 'mocks_manifest.json'), 'w') as f:
        json.dump(manifest, f, indent=1)
    print(f"wrote {n_mocks + 1} mock dirs under {OUT}")


if __name__ == '__main__':
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    s = int(sys.argv[2]) if len(sys.argv) > 2 else 42
    main(n, s)
