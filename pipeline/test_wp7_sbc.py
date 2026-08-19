import numpy as np

from pipeline.wp7_sbc import FS7MockBackground, draw_truth


def test_sbc_truth_is_deterministic_physical_and_finite():
    first, background1 = draw_truth(1)
    second, background2 = draw_truth(1)
    assert first == second
    probes = np.asarray([0.1, 0.5, 1.0, 2.0, 4.0])
    assert np.all(np.isfinite(background1.angular_diameter_distance(probes)))
    assert np.all(np.isfinite(background2.hubble_parameter(probes)))
    assert background1.rdrag == background2.rdrag
    assert "fate" not in first
