import numpy as np

from pipeline.make_mocks import truth_background


BASE_TRUTH = {
    "ombh2": 0.02263,
    "omch2": 0.11724,
    "H0": 68.81,
}


def test_lcdm_default_matches_explicit_cpl_boundary():
    implicit = truth_background(BASE_TRUTH)
    explicit = truth_background({**BASE_TRUTH, "w": -1.0, "wa": 0.0})
    redshifts = np.array([0.1, 0.5, 1.0, 2.0])
    np.testing.assert_allclose(
        implicit.angular_diameter_distance(redshifts),
        explicit.angular_diameter_distance(redshifts),
        rtol=0,
        atol=0,
    )


def test_off_boundary_truth_changes_background_prediction():
    lcdm = truth_background(BASE_TRUTH)
    off_boundary = truth_background({**BASE_TRUTH, "w": -0.9, "wa": 0.3})
    redshifts = np.array([0.5, 1.0, 2.0])
    assert not np.allclose(
        lcdm.angular_diameter_distance(redshifts),
        off_boundary.angular_diameter_distance(redshifts),
        rtol=1e-8,
        atol=0,
    )
