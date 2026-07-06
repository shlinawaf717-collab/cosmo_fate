"""Fate classifier — frozen plan §5, background model §1.

Classifies each posterior sample by integrating the background from a=1
to a_max=1e4. Priority order: CRUNCH > RIP > DS > DECAY > OTHER.
Boundary flag: classification flips when thresholds are doubled/halved.

Background (§1): H²/H0² = Ωr a⁻⁴ + Ωm a⁻³ + Ωk a⁻² + ΩDE·f_DE(a),
Ωr derived from T_CMB=2.7255 K, N_eff=3.044 (massless approx),
ΩDE = 1 − Ωm − Ωk − Ωr (closure).
"""

import numpy as np
from scipy.integrate import quad

TCMB = 2.7255
NEFF = 3.044
OMEGA_GAMMA_H2 = 2.4729e-5 * (TCMB / 2.7255) ** 4
OMEGA_R_H2 = OMEGA_GAMMA_H2 * (1.0 + 0.2271 * NEFF)

A_MAX = 1.0e4
THRESH = dict(rip_rel=1e-3, ds_w=0.01, decay_ratio=0.01, decay_vs_m=1.0, asym_eps=0.01)
_EXP_CAP = 700.0


def ln_fde_cpl(a, w0, wa):
    """log of rho_DE(a)/rho_DE(1) for CPL."""
    return -3.0 * (1.0 + w0 + wa) * np.log(a) - 3.0 * wa * (1.0 - a)


def w_cpl(a, w0, wa):
    return w0 + wa * (1.0 - a)


class Background:
    def __init__(self, omegam, H0, omk=0.0, w0=-1.0, wa=0.0,
                 ln_fde=None, w_of_a=None, w_inf=None):
        h2 = (H0 / 100.0) ** 2
        self.om = omegam
        self.omr = OMEGA_R_H2 / h2
        self.omk = omk
        self.ode = 1.0 - omegam - omk - self.omr
        self.w0, self.wa = w0, wa
        self.ln_fde = ln_fde or (lambda a: ln_fde_cpl(a, w0, wa))
        self.w_of_a = w_of_a or (lambda a: w_cpl(a, w0, wa))
        self.w_inf = w_inf  # finite limit of w(a) as a->inf, if it exists (A-003)

    def E2(self, a):
        lf = self.ln_fde(a)
        fde = np.inf if lf > _EXP_CAP else np.exp(lf)
        return (self.omr * a ** -4 + self.om * a ** -3
                + self.omk * a ** -2 + self.ode * fde)

    def rho_de_ratio(self, a):
        lf = self.ln_fde(a)
        return np.inf if lf > _EXP_CAP else np.exp(lf)

    def t_of(self, a_end):
        """cosmic time from a=1 to a_end in units of 1/H0 (inf if H²<=0 hit)."""
        def integrand(a):
            e2 = self.E2(a)
            if not np.isfinite(e2):
                return 0.0
            if e2 <= 0:
                raise _CrunchSignal
            return 1.0 / (a * np.sqrt(e2))
        # log-spaced piecewise quad for numerical robustness
        edges = np.geomspace(1.0, a_end, 40)
        tot = 0.0
        for lo, hi in zip(edges[:-1], edges[1:]):
            tot += quad(integrand, lo, hi, limit=100)[0]
        return tot


class _CrunchSignal(Exception):
    pass


def classify(bg, thresh=None):
    """Return (label, boundary_flag). Implements §5 exactly."""
    th = dict(THRESH)
    if thresh:
        th.update(thresh)

    label = _classify_once(bg, th)
    # boundary check: thresholds x2 and /2 (§5)
    flips = False
    for fac in (2.0, 0.5):
        th2 = {k: v * fac for k, v in th.items()}
        if _classify_once(bg, th2) != label:
            flips = True
            break
    return label, flips


def _classify_once(bg, th):
    # 1. CRUNCH: exists a>=1 with H²<=0
    agrid = np.geomspace(1.0, A_MAX, 400)
    e2 = np.array([bg.E2(a) for a in agrid])
    finite = e2[np.isfinite(e2)]
    if finite.size and (finite <= 0).any():
        return "CRUNCH"

    # A-003 asymptotic branch: analytic criteria when w(a) has a finite limit
    if getattr(bg, 'w_inf', None) is not None:
        eps = th["asym_eps"]
        if bg.w_inf < -1.0 - eps:
            return "RIP"          # constant-w<-1 finite-time singularity (analytic)
        if abs(bg.w_inf + 1.0) <= eps and bg.ode > 0:
            return "DS"
        return "DECAY"

    # 2. RIP: t(A_MAX) converged w.r.t. t(2*A_MAX)
    try:
        t1 = bg.t_of(A_MAX)
        t2 = bg.t_of(2 * A_MAX)
    except _CrunchSignal:
        return "CRUNCH"
    if t1 > 0 and (t2 - t1) / t1 < th["rip_rel"]:
        return "RIP"

    # 3. DS: rho_DE(A_MAX) > 0 and |w(A_MAX)+1| < th
    rho = bg.rho_de_ratio(A_MAX)
    if bg.ode * rho > 0 and abs(bg.w_of_a(A_MAX) + 1.0) < th["ds_w"]:
        return "DS"

    # 4. DECAY: rho_DE(A_MAX)/rho_DE(1) < th  or  rho_DE/rho_m(A_MAX) < th
    rho_m = bg.om * A_MAX ** -3
    if (np.isfinite(rho) and rho < th["decay_ratio"]) or \
       (np.isfinite(rho) and bg.ode * rho / rho_m < th["decay_vs_m"]):
        return "DECAY"

    return "OTHER"


THERMO = {"DS": "heat-death-compatible", "DECAY": "heat-death-compatible",
          "RIP": "non-heat-death", "CRUNCH": "non-heat-death",
          "OTHER": "unclassified"}
