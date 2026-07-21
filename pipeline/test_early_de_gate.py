import numpy as np
import pytest

from pipeline.wparams import (
    EARLY_DE_MAX_RATIO,
    Z_EARLY_DE_GATE,
    bin4_early_de_ratio,
    make_ln_fde,
)


def test_bin4_early_de_ratio_matches_background_integral():
    p = {"w1": -0.9, "w2": -1.1, "w3": -1.3, "w4": -0.7}
    om, H0 = 0.3, 68.0
    a = 1.0 / (1.0 + Z_EARLY_DE_GATE)
    omr = 2.4729e-5 * (1.0 + 0.2271 * 3.044) / (H0 / 100.0) ** 2
    numeric = (1.0 - om - omr) * np.exp(make_ln_fde("bin4", p)(a)) / (om * a ** -3)
    exact = bin4_early_de_ratio(om, H0, **p)
    # make_ln_fde uses a finite 4000-point interpolation grid; the gate uses
    # the exact piecewise integral and should agree at the percent level.
    assert exact == pytest.approx(numeric, rel=1e-2)


def test_w4_less_than_zero_is_not_sufficient_gate():
    unsafe = bin4_early_de_ratio(0.3, 68.0, -1.0, -1.0, -1.0, -0.01)
    safe = bin4_early_de_ratio(0.3, 68.0, -1.0, -1.0, -1.0, -1.0)
    assert unsafe > EARLY_DE_MAX_RATIO
    assert safe < EARLY_DE_MAX_RATIO
