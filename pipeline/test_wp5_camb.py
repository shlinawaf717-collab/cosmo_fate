from types import SimpleNamespace

import pytest

from cobaya.theories.camb.camb import CAMB

from pipeline.wp5_camb import BIN4CAMB, BIN4_PARAMETERS


def test_bin4_parameter_names_are_fixed():
    assert BIN4_PARAMETERS == ("w1", "w2", "w3", "w4")


def test_bin4_camb_rejects_unregistered_width_before_camb_import():
    theory = object.__new__(BIN4CAMB)
    theory.delta_lna = 0.03
    theory.log = None
    with pytest.raises(Exception):
        theory.initialize()


def test_bin4_camb_installs_history_inside_theta_h0_solver(monkeypatch):
    captured = {}
    params = SimpleNamespace(H0=None, omegam=0.3, DarkEnergy=None)

    def fake_set(self, standard, state):
        captured.update(standard)
        standard["setter_H0"](params, 71.0)
        return params

    monkeypatch.setattr(CAMB, "set", fake_set)
    theory = object.__new__(BIN4CAMB)
    theory.delta_lna = 0.01
    theory.table_base_points = 1200
    theory.table_points_per_transition = 240
    values = {
        "cosmomc_theta": 0.01041,
        "ombh2": 0.0224,
        "omch2": 0.12,
        "w1": -1.0,
        "w2": -0.9,
        "w3": -1.5,
        "w4": -1.7,
    }

    result = theory.set(values, {})

    assert result is params
    assert params.H0 == 71.0
    assert params.DarkEnergy is not None
    assert callable(captured["setter_H0"])
    assert not set(BIN4_PARAMETERS).intersection(captured)


def test_bin4_camb_rejects_registered_early_de_failure_before_transfers(monkeypatch):
    params = SimpleNamespace(H0=70.0, omegam=0.3, DarkEnergy=None)

    def fake_set(self, standard, state):
        standard["setter_H0"](params, 70.0)
        return params

    monkeypatch.setattr(CAMB, "set", fake_set)
    theory = object.__new__(BIN4CAMB)
    theory.delta_lna = 0.01
    theory.table_base_points = 1200
    theory.table_points_per_transition = 240
    values = {
        "cosmomc_theta": 0.01041,
        "ombh2": 0.0224,
        "omch2": 0.12,
        "w1": -1.0,
        "w2": -0.9,
        "w3": -1.5,
        "w4": -0.01,
    }

    assert theory.set(values, {}) is False
