import numpy as np

from pipeline.build_wp7_configs import SETTINGS, build
from pipeline.wp7_fs7 import admissibility, latent_to_nodes


def test_all_registered_settings_use_noncentred_standard_normals():
    for tag, (sigma, ell, prior_function) in SETTINGS.items():
        info = build(tag)
        assert info["theory"]["pipeline.bgtheory.BackgroundW"]["model"] == "fs7"
        assert prior_function in info["prior"]["fs7_function_bounds"]
        for index in range(1, 8):
            param = info["params"][f"z{index}"]
            assert param["prior"] == {"dist": "norm", "loc": 0.0, "scale": 1.0}
            assert param["drop"] is True
            assert f"fs7_w{index}" in info["params"]
        assert admissibility(latent_to_nodes(np.zeros(7), sigma, ell)).admissible


def test_development_configs_forbid_posterior_and_evidence_claims():
    info = build("primary")
    metadata = info["wp7_metadata"]
    assert metadata["role"].startswith("development")
    assert "evidence forbidden" in metadata["external_prior_normalization"]
