"""Dark-energy w(a) parametrizations for the F_param axis (frozen plan §1 table).

Each model provides: param names, w(a), and ln f_DE(a) = ln[rho_DE(a)/rho_DE(1)].
ln f_DE = 3 * integral_a^1 (1+w(a'))/a' da'  (numeric on a log grid, cached per point).
Future branch (a>1) follows the same w(a) except BIN4, which freezes w = w1 (first bin).
"""

import numpy as np

Z_EDGES_BIN4 = (0.0, 0.3, 0.7, 1.5, 1100.0)  # frozen §1
_AGRID = np.geomspace(1e-9, 1e5, 4000)
_LNA = np.log(_AGRID)


def w_cpl(a, p):
    return p['w'] + p['wa'] * (1.0 - a)


def w_ba(a, p):
    z = 1.0 / a - 1.0
    return p['w'] + p['wa'] * z / (1.0 + z * z)


def w_jbp(a, p):
    z = 1.0 / a - 1.0
    return p['w'] + p['wa'] * z / (1.0 + z) ** 2


def w_bin4(a, p):
    a = np.asarray(a, dtype=float)
    z = 1.0 / a - 1.0
    w = np.full_like(a, p['w1'])
    for i, (zlo, zhi) in enumerate(zip(Z_EDGES_BIN4[:-1], Z_EDGES_BIN4[1:]), 1):
        w = np.where((z >= zlo) & (z < zhi), p[f'w{i}'], w)
    w = np.where(z >= Z_EDGES_BIN4[-1], p['w4'], w)
    w = np.where(z < 0.0, p['w1'], w)   # future: freeze first-bin value (frozen §1)
    return w if w.shape else float(w)


# --- GP reconstruction (frozen plan §1: SE kernel, hyperparams (sigma_f, ell)
# sampled hierarchically, mean function w = -1). Realization: 6 nodes uniform
# in ln a over a in [0.25, 1] (z in [0, 3], the constrained window); w(a)
# elsewhere is the GP conditional mean given the nodes, which reverts to the
# mean -1 on the correlation scale ell (e-folds). Consequences, by construction:
# early-time w -> -1 (matter domination automatic; P1 intent satisfied) and
# w(a->inf) = -1 exactly, so the asymptotic branch (A-003) classifies every
# sample DS: the fate verdict is donated by the mean function, not the data.
# sigma_f cancels in the conditional mean; it acts only in the prior amplitude.
GP_LNA_NODES = np.linspace(0.0, np.log(0.25), 6)   # w1 at z=0 ... w6 at z=3
GP_JITTER = 1e-10


def _gp_corr(dx2, ell):
    return np.exp(-0.5 * dx2 / (ell * ell))


def w_gp(a, p):
    x = np.log(np.asarray(a, dtype=float))
    y = np.array([p[f'w{i}'] for i in range(1, 7)]) + 1.0
    X = GP_LNA_NODES
    ell = p['gp_ell']
    K = _gp_corr((X[:, None] - X[None, :]) ** 2, ell) + GP_JITTER * np.eye(6)
    kx = _gp_corr((x[..., None] - X) ** 2, ell)
    w = -1.0 + kx @ np.linalg.solve(K, y)
    return w if w.shape else float(w)


_GP_PRIOR_CACHE = {}


def gp_logprior(y_nodes, sigf, ell):
    """log N(w_nodes; mean=-1, sigf^2 * K_SE(ell)) — the hierarchical GP prior."""
    key = (round(float(sigf), 10), round(float(ell), 10))
    if key not in _GP_PRIOR_CACHE:
        if len(_GP_PRIOR_CACHE) > 100000:
            _GP_PRIOR_CACHE.clear()
        X = GP_LNA_NODES
        C = sigf * sigf * _gp_corr((X[:, None] - X[None, :]) ** 2, ell) \
            + GP_JITTER * np.eye(6)
        L = np.linalg.cholesky(C)
        _GP_PRIOR_CACHE[key] = (np.linalg.inv(L), 2.0 * np.log(np.diag(L)).sum())
    Linv, logdet = _GP_PRIOR_CACHE[key]
    d = Linv @ (np.asarray(y_nodes, dtype=float) + 1.0)
    return -0.5 * (d @ d + logdet + 6.0 * np.log(2.0 * np.pi))


MODELS = {
    'cpl':  {'params': ['w', 'wa'],           'w_of_a': w_cpl,  'w_inf': None},
    'ba':   {'params': ['w', 'wa'],           'w_of_a': w_ba,   'w_inf': lambda p: p['w'] - 0.5 * p['wa']},
    'jbp':  {'params': ['w', 'wa'],           'w_of_a': w_jbp,  'w_inf': None},
    'bin4': {'params': ['w1', 'w2', 'w3', 'w4'], 'w_of_a': w_bin4, 'w_inf': lambda p: p['w1']},
    'gp':   {'params': ['w1', 'w2', 'w3', 'w4', 'w5', 'w6', 'gp_sigf', 'gp_ell'],
             'w_of_a': w_gp, 'w_inf': lambda p: -1.0},
}


def make_ln_fde(model, p):
    """Return callable ln_fde(a) with ln_fde(1)=0, valid for a in [1e-9, 1e5]."""
    w = MODELS[model]['w_of_a'](_AGRID, p)
    integrand = 3.0 * (1.0 + w)
    cum = np.concatenate([[0.0], np.cumsum(0.5 * (integrand[1:] + integrand[:-1])
                                           * np.diff(_LNA))])
    cum1 = np.interp(0.0, _LNA, cum)
    lnf_grid = -(cum - cum1)          # ln f = -int_{ln 1}^{ln a} 3(1+w) dlna
    def ln_fde(a):
        return np.interp(np.log(a), _LNA, lnf_grid)
    ln_fde.grid = (_AGRID, lnf_grid)
    return ln_fde


def make_w_of_a(model, p):
    f = MODELS[model]['w_of_a']
    return lambda a: f(a, p)
