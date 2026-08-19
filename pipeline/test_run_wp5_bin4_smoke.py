from pipeline.run_wp5_bin4_smoke import audit_log


def test_smoke_log_requires_all_full_likelihood_markers():
    text = "\n".join([
        "[pipeline.wp5_camb.bin4camb] loaded",
        "[bao.desi_dr2.desi_bao_all] Initialized.",
        "Checking likelihood one", "Checking likelihood two",
        "Number of data points: 9915",
        "Loading ACT DR6 lensing likelihood v1.2",
        "This run has been SEEDED w1:1 w2:2 w3:3 w4:4",
        "Test initialization successful",
    ])
    assert all(audit_log(text).values())
