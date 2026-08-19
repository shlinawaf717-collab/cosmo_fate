from pipeline.build_wp5_bin4_configs import build_config


def test_wp5_config_replaces_cpl_with_four_bins_and_ppf_adapter():
    info = build_config(0.01)
    assert "camb" not in info["theory"]
    theory = info["theory"]["pipeline.wp5_camb.BIN4CAMB"]
    assert theory["delta_lna"] == 0.01
    assert all(name in info["params"] for name in ("w1", "w2", "w3", "w4"))
    assert "w" not in info["params"] and "wa" not in info["params"]
    assert info["prior"] == {"matter_dom_bin4": "lambda w4: 0 if w4 < 0 else -1e30"}
    assert "pipeline.early_de_gate.Bin4EarlyDEGate" in info["likelihood"]
    assert info["sampler"]["mcmc"]["covmat"] is None


def test_wp5_width_changes_only_registered_theory_and_identity_fields():
    low = build_config(0.005); high = build_config(0.02)
    assert low["theory"]["pipeline.wp5_camb.BIN4CAMB"]["delta_lna"] == 0.005
    assert high["theory"]["pipeline.wp5_camb.BIN4CAMB"]["delta_lna"] == 0.02
