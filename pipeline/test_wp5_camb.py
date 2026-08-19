import pytest

from pipeline.wp5_camb import BIN4CAMB, BIN4_PARAMETERS


def test_bin4_parameter_names_are_fixed():
    assert BIN4_PARAMETERS == ("w1", "w2", "w3", "w4")


def test_bin4_camb_rejects_unregistered_width_before_camb_import():
    theory = object.__new__(BIN4CAMB)
    theory.delta_lna = 0.03
    theory.log = None
    with pytest.raises(Exception):
        theory.initialize()
