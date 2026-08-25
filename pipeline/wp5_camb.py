"""Cobaya CAMB theory adapter for the perturbation-consistent WP5 BIN4 model."""

from __future__ import annotations

import numpy as np

from cobaya.theories.camb.camb import CAMB, CambTransfers
from cobaya.log import LoggedError

from pipeline.wp5_bin4 import SENSITIVITY_DELTAS, make_bin4_ppf
from pipeline.wparams import (
    EARLY_DE_MAX_RATIO,
    Z_EARLY_DE_GATE,
    bin4_early_de_ratio,
)


BIN4_PARAMETERS = ("w1", "w2", "w3", "w4")


class BIN4CAMB(CAMB):
    """Standard Cobaya CAMB with a sampled tabulated DarkEnergyPPF history."""

    delta_lna: float = 0.01
    table_base_points: int = 1200
    table_points_per_transition: int = 240

    def initialize(self):
        if self.delta_lna not in SENSITIVITY_DELTAS:
            raise LoggedError(
                self.log,
                "WP5 delta_lna=%s is outside the frozen set %s",
                self.delta_lna,
                SENSITIVITY_DELTAS,
            )
        if self.table_base_points < 100 or self.table_points_per_transition < 20:
            raise LoggedError(self.log, "WP5 table resolution is invalid")
        super().initialize()

    def set(self, params_values_dict, state):
        missing = set(BIN4_PARAMETERS).difference(params_values_dict)
        if missing:
            raise LoggedError(self.log, "Missing WP5 BIN4 parameters: %s", sorted(missing))
        values = tuple(float(params_values_dict[name]) for name in BIN4_PARAMETERS)
        dark_energy = make_bin4_ppf(
            *values,
            delta_lna=float(self.delta_lna),
            base_points=int(self.table_base_points),
            points_per_transition=int(self.table_points_per_transition),
        )

        # CAMB's theta -> H0 solver must see the sampled dark-energy history
        # during every root evaluation. Assigning DarkEnergy only after
        # ``super().set`` solves H0 for the base LCDM history and then changes
        # the background underneath the solved acoustic scale. Besides
        # targeting the wrong posterior, that inconsistent state can reach a
        # fatal Fortran ``thermo out of bounds`` branch that cannot be caught
        # by Cobaya's normal ``stop_at_error: false`` handling.
        def set_h0_with_bin4(params, h0):
            params.H0 = h0
            params.DarkEnergy = dark_energy

        standard = {
            name: value for name, value in params_values_dict.items()
            if name not in BIN4_PARAMETERS
        }
        standard["setter_H0"] = set_h0_with_bin4
        params = super().set(standard, state)
        if not params:
            return False
        # Keep the final parameter object explicit as well as the temporary
        # objects used by the theta root finder.
        params.DarkEnergy = dark_energy
        # The registered early-DE likelihood is evaluated only after CAMB has
        # produced theory products. Some points that it would assign -inf can
        # therefore reach CAMB first and terminate the whole Python process in
        # a Fortran ERROR STOP. Apply the identical frozen predicate here as a
        # theory precondition, so those same zero-likelihood points are
        # rejected before transfer/thermodynamics. This does not narrow or
        # otherwise change the target support.
        ratio = bin4_early_de_ratio(
            params.omegam,
            params.H0,
            *values,
            z=Z_EARLY_DE_GATE,
        )
        if not np.isfinite(ratio) or ratio >= EARLY_DE_MAX_RATIO:
            return False
        return params

    def get_helper_theories(self):
        self._camb_transfers = BIN4CambTransfers(
            self,
            "camb.transfers",
            {"stop_at_error": self.stop_at_error},
            timing=self.timer,
        )
        self._camb_transfers.requires = self._transfer_requires
        return {"camb.transfers": self._camb_transfers}


class BIN4CambTransfers(CambTransfers):
    """Advertise the four BIN4 nodes as slow CAMB-transfer parameters."""

    def get_can_support_params(self):
        return super().get_can_support_params().union(BIN4_PARAMETERS)
