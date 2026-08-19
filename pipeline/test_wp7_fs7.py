import numpy as np
import pytest

from pipeline.wp7_development_preflight import build
from pipeline.wp7_fs7 import (
    ALL_A_NODES,
    FS7Error,
    admissibility,
    admissible_latent_mask,
    conditional_future_geometry,
    draw_truncated_latents,
    latent_to_nodes,
    make_ln_fde,
    nodes_to_latent,
    spline,
    w_of_a,
)


def test_lcdm_identity_and_constant_extensions():
    nodes = np.full(7, -1.0)
    probes = np.asarray([1e-6, 0.25, 0.4, 1.0, 4.0, 1e4])
    np.testing.assert_allclose(w_of_a(probes, nodes), -1.0, rtol=0, atol=1e-15)
    np.testing.assert_allclose(w_of_a(ALL_A_NODES, nodes), -1.0, rtol=0, atol=1e-15)
    np.testing.assert_allclose(make_ln_fde(nodes)(probes), 0.0, rtol=0, atol=1e-13)


def test_noncentred_transform_roundtrips_all_registered_settings():
    z = np.asarray([0.2, -0.15, 0.1, -0.05, 0.08, -0.04, 0.02])
    for sigma, ell in ((0.5, 0.7), (0.25, 0.7), (1.0, 0.7), (0.5, 0.35), (0.5, 1.4)):
        nodes = latent_to_nodes(z, sigma, ell)
        np.testing.assert_allclose(nodes_to_latent(nodes, sigma, ell), z, rtol=0, atol=1e-8)


def test_registered_spline_interpolates_nodes_and_is_clamped():
    nodes = np.asarray([-0.9, -1.1, -0.8, -1.0, -1.2, -0.7, -1.05])
    curve = spline(nodes)
    np.testing.assert_allclose(w_of_a(ALL_A_NODES[1:], nodes), nodes, rtol=0, atol=1e-14)
    assert abs(curve.derivative()(np.log(ALL_A_NODES[0]))) < 1e-13
    assert abs(curve.derivative()(np.log(ALL_A_NODES[-1]))) < 1e-13


def test_admissibility_catches_node_and_spline_overshoot():
    assert admissibility(np.full(7, -1.0)).admissible
    bad_node = np.full(7, -1.0); bad_node[2] = 1.1
    assert not admissibility(bad_node).nodes_within_bounds
    overshoot = np.asarray([-3.0, 1.0, -3.0, 1.0, -3.0, 1.0, -3.0])
    report = admissibility(overshoot)
    assert report.nodes_within_bounds
    assert not report.spline_within_bounds


def test_primary_and_short_length_geometry_match_registered_prediction():
    primary = conditional_future_geometry(0.5, 0.7)
    assert primary["conditional_sd"] == pytest.approx(0.4650873176547938)
    assert primary["multiple_R2"] == pytest.approx(0.1347751481727658)
    short = conditional_future_geometry(0.5, 0.35)
    assert short["multiple_R2"] < 1e-6


def test_invalid_coordinates_are_rejected():
    with pytest.raises(FS7Error):
        latent_to_nodes([0.0] * 6, 0.5, 0.7)
    with pytest.raises(FS7Error):
        w_of_a(0.0, np.full(7, -1.0))


def test_vectorized_truncation_matches_scalar_admissibility():
    latent = np.asarray([
        np.zeros(7),
        [8.0, 0, 0, 0, 0, 0, 0],
        [0.2, -0.1, 0.05, 0, 0.1, -0.05, 0.02],
    ])
    mask = admissible_latent_mask(latent, 0.5, 0.7)
    expected = [admissibility(latent_to_nodes(row, 0.5, 0.7)).admissible for row in latent]
    np.testing.assert_array_equal(mask, expected)


def test_admissibility_is_symmetric_about_w_minus_one():
    z = np.asarray([
        [0.2, -0.1, 0.05, 0.0, 0.1, -0.05, 0.02],
        [3.0, -1.0, 2.0, 0.5, -0.2, 0.7, -1.1],
    ])
    np.testing.assert_array_equal(
        admissible_latent_mask(z, 1.0, 0.7),
        admissible_latent_mask(-z, 1.0, 0.7),
    )


def test_direct_rejection_sampler_is_deterministic_and_admissible():
    first, audit1 = draw_truncated_latents(32, 1.0, 0.7, seed=2026090101, batch_size=64)
    second, audit2 = draw_truncated_latents(32, 1.0, 0.7, seed=2026090101, batch_size=64)
    np.testing.assert_array_equal(first, second)
    assert audit1 == audit2
    assert np.all(admissible_latent_mask(first, 1.0, 0.7))
    assert not audit1["fate_composition_calculated"]


def test_development_preflight_is_endpoint_blind():
    report = build()
    assert report["status"] == "PASS_WITH_ELL_1P4_WARNING"
    assert not report["prior_simulation_performed"]
    assert not report["likelihood_evaluation_performed"]
    assert not report["posterior_sampling_performed"]
    assert not report["fate_endpoint_calculated"]
