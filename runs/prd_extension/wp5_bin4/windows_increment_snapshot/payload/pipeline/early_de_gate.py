"""Hard early-dark-energy validity gate for the BIN4 compressed-CMB fit."""

import numpy as np
from cobaya.likelihood import Likelihood

from pipeline.wparams import EARLY_DE_MAX_RATIO, Z_EARLY_DE_GATE, bin4_early_de_ratio


class Bin4EarlyDEGate(Likelihood):
    z_check = Z_EARLY_DE_GATE
    max_ratio = EARLY_DE_MAX_RATIO

    def get_requirements(self):
        return {name: None for name in ("omegam", "H0", "w1", "w2", "w3", "w4")}

    def logp(self, **params_values):
        p = self.provider.get_param
        ratio = bin4_early_de_ratio(
            p("omegam"), p("H0"), p("w1"), p("w2"), p("w3"), p("w4"),
            z=self.z_check,
        )
        return 0.0 if np.isfinite(ratio) and ratio < self.max_ratio else -np.inf
