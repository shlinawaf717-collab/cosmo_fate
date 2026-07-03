"""Planck 2018 compressed distance-prior likelihood (R, l_A, Omega_b h^2).

Numbers: Chen, Huang & Wang 2018 (arXiv:1808.05724), Table I, LCDM row,
Planck 2018 TT,TE,EE+lowE. Registered in data/MANIFEST.md.

Theory side follows that paper's own conventions exactly (its eqs. 1-6 and
the z_* fitting formula, eqs. 8-10) rather than CAMB's recombination z_*:
the priors were extracted with these formulas, so the same formulas must be
used to predict (R, l_A). Mixing conventions shifts l_A by ~3 sigma.
Verified at the Planck 2018 LCDM mean: reproduces (R, l_A) to <0.2 sigma.
"""

import numpy as np
from scipy.integrate import quad
from cobaya.likelihood import Likelihood

C_KMS = 299792.458
TCMB = 2.7255


class PlanckDistPrior(Likelihood):
    mean = np.array([1.7502, 301.471, 0.02236])  # R, l_A, Omega_b h^2
    sigma = np.array([0.0046, 0.090, 0.00015])
    corr = np.array([
        [1.00, 0.46, -0.66],
        [0.46, 1.00, -0.33],
        [-0.66, -0.33, 1.00],
    ])

    def initialize(self):
        cov = self.corr * np.outer(self.sigma, self.sigma)
        self.icov = np.linalg.inv(cov)

    def get_requirements(self):
        return {"ombh2": None, "omegam": None, "H0": None,
                "w": None, "wa": None, "omk": None}

    def logp(self, **params_values):
        p = self.provider.get_param
        ombh2, om, H0 = p("ombh2"), p("omegam"), p("H0")
        w0, wa, omk = p("w"), p("wa"), p("omk")
        h2 = (H0 / 100.0) ** 2
        omh2 = om * h2
        tfac = (TCMB / 2.7) ** -4

        # z_* fitting formula (Hu & Sugiyama), paper eqs. (8)-(10)
        g1 = 0.0738 * ombh2 ** -0.238 / (1 + 39.5 * ombh2 ** 0.763)
        g2 = 0.560 / (1 + 21.1 * ombh2 ** 1.81)
        zstar = 1048 * (1 + 0.00124 * ombh2 ** -0.738) * (1 + g1 * omh2 ** g2)

        # radiation density, paper eq. (6)
        zeq = 2.5e4 * omh2 * tfac
        omr = om / (1 + zeq)
        ode = 1.0 - om - omk - omr

        def E(z):
            a = 1.0 / (1 + z)
            fde = a ** (-3 * (1 + w0 + wa)) * np.exp(-3 * wa * (1 - a))
            return np.sqrt(omr * (1 + z) ** 4 + om * (1 + z) ** 3
                           + omk * (1 + z) ** 2 + ode * fde)

        # comoving distance to z_* [Mpc]
        dh = C_KMS / H0
        chi = dh * quad(lambda z: 1.0 / E(z), 0, zstar, limit=200)[0]
        if omk > 1e-8:
            sk = np.sqrt(omk)
            DM = dh / sk * np.sinh(sk * chi / dh)
        elif omk < -1e-8:
            sk = np.sqrt(-omk)
            DM = dh / sk * np.sin(sk * chi / dh)
        else:
            DM = chi

        # sound horizon r_s(z_*), paper eq. (3)
        rb = 31500.0 * ombh2 * tfac  # 3 rho_b / (4 rho_gamma) per unit a
        astar = 1.0 / (1 + zstar)
        rs = dh * quad(
            lambda a: 1.0 / (a * a * E(1.0 / a - 1) * np.sqrt(3 * (1 + rb * a))),
            1e-9, astar, limit=200)[0]

        lA = np.pi * DM / rs
        R = np.sqrt(om) * H0 * DM / C_KMS
        d = np.array([R, lA, ombh2]) - self.mean
        return -0.5 * d @ self.icov @ d
