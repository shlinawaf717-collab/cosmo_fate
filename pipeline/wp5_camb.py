"""Cobaya CAMB theory adapter for the perturbation-consistent WP5 BIN4 model."""

from __future__ import annotations

from cobaya.theories.camb.camb import CAMB, CambTransfers
from cobaya.log import LoggedError

from pipeline.wp5_bin4 import SENSITIVITY_DELTAS, make_bin4_ppf


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
        standard = {
            name: value for name, value in params_values_dict.items()
            if name not in BIN4_PARAMETERS
        }
        params = super().set(standard, state)
        if not params:
            return False
        params.DarkEnergy = make_bin4_ppf(
            *values,
            delta_lna=float(self.delta_lna),
            base_points=int(self.table_base_points),
            points_per_transition=int(self.table_points_per_transition),
        )
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
