"""Gate-2 mock generator (frozen plan §7.4).

Truth = LCDM best fit on D0 (runs/gate2/truth_lcdm_d0.json).
For each mock: draw SN / BAO / CMB-prior data from the exact covariances used
by the likelihoods, around the truth predictions computed with the same code
paths (camb background; predict_R_lA for the CMB prior).

Usage: .venv/bin/python pipeline/make_mocks.py [n_mocks=100] [seed=42]
Mock 000 is always generated with ZERO noise (pipeline validation: chi2~0 at truth).
"""

import sys, os, json, shutil
import numpy as np
import camb

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
from pipeline.cmb_distprior import predict_R_lA, PlanckDistPrior

DATA = os.path.join(ROOT, 'data/cobaya_packages/data')
SN_DIR = os.path.join(DATA, 'sn_data/PantheonPlus')
BAO_DIR = os.path.join(DATA, 'bao_data/desi_bao_dr2')
OUT = os.path.join(ROOT, 'runs/gate2/mocks')
C_KMS = 299792.458


def truth_background(t):
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


def main(n_mocks=100, seed=42):
    t = json.load(open(os.path.join(ROOT, 'runs/gate2/truth_lcdm_d0.json')))
    bg = truth_background(t)
    rng = np.random.default_rng(seed)

    # --- truth predictions
    df, sn_mu, sn_mask = sn_pred(bg, t)
    sn_cov = load_sn_cov()
    Csub = sn_cov[np.ix_(sn_mask, sn_mask)]
    L_sn = np.linalg.cholesky(Csub)
    print(f"SN: {sn_mask.sum()} used rows of {len(sn_mu)}")

    bao_rows = bao_pred(bg)
    bao_mu = np.array([v for _, v, _ in bao_rows])
    bao_cov = np.loadtxt(os.path.join(BAO_DIR, 'desi_gaussian_bao_ALL_GCcomb_cov.txt'))
    L_bao = np.linalg.cholesky(bao_cov)

    R, lA = predict_R_lA(t['ombh2'], t['omegam'], t['H0'], -1.0, 0.0)
    cmb_mu = np.array([R, lA, t['ombh2']])
    pl = PlanckDistPrior  # class attrs hold fiducial sigma/corr
    sig = np.asarray(pl.sigma, float)
    cmb_cov = np.asarray(pl.corr, float) * np.outer(sig, sig)
    L_cmb = np.linalg.cholesky(cmb_cov)
    print("CMB truth pred:", cmb_mu)

    os.makedirs(OUT, exist_ok=True)
    manifest = []
    for k in range(n_mocks + 1):          # k=0 : zero-noise validation mock
        d = os.path.join(OUT, f'm{k:03d}')
        os.makedirs(d, exist_ok=True)
        noise = 0.0 if k == 0 else 1.0

        # SN
        mock_mag = df['m_b_corr'].values.copy()
        mock_mag[sn_mask] = sn_mu[sn_mask] + noise * (L_sn @ rng.standard_normal(sn_mask.sum()))
        dfm = df.copy()
        dfm['m_b_corr'] = mock_mag
        dfm.to_csv(os.path.join(d, 'sn_mock.dat'), sep=' ', index=False)
        for target, link in [('Pantheon+SH0ES_STAT+SYS.cov', 'sn_cov.cov')]:
            p = os.path.join(d, link)
            if not os.path.lexists(p):
                os.symlink(os.path.join(SN_DIR, target), p)
        with open(os.path.join(d, 'config.dataset'), 'w') as f:
            f.write("name = PANTHEONPLUS_MOCK\ndata_file = sn_mock.dat\n"
                    "mag_covmat_file = sn_cov.cov\n")

        # BAO
        vals = bao_mu + noise * (L_bao @ rng.standard_normal(len(bao_mu)))
        with open(os.path.join(d, 'bao_mean.txt'), 'w') as f:
            f.write("# [z] [value at z] [quantity]\n")
            for (z, _, q), v in zip(bao_rows, vals):
                f.write(f"{z:.8f} {v:.8f} {q}\n")
        p = os.path.join(d, 'bao_cov.txt')
        if not os.path.lexists(p):
            os.symlink(os.path.join(BAO_DIR, 'desi_gaussian_bao_ALL_GCcomb_cov.txt'), p)

        # CMB prior draw
        cmb = cmb_mu + noise * (L_cmb @ rng.standard_normal(3))
        json.dump({"mean": cmb.tolist()}, open(os.path.join(d, 'cmb_mean.json'), 'w'))

        manifest.append(d)

    json.dump({"truth": t, "seed": seed, "n": n_mocks,
               "cmb_truth_pred": cmb_mu.tolist()},
              open(os.path.join(OUT, 'mocks_manifest.json'), 'w'), indent=1)
    print(f"wrote {len(manifest)} mock dirs under {OUT}")


if __name__ == '__main__':
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    s = int(sys.argv[2]) if len(sys.argv) > 2 else 42
    main(n, s)
