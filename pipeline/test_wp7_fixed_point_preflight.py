from pipeline.wp7_fixed_point_preflight import run


def test_fs7_lcdm_and_dual_path_fixed_points_pass_without_endpoint():
    result = run()
    assert result["status"] == "PASS"
    assert all(result["gates"].values())
    assert not result["posterior_sampling_performed"]
    assert not result["fate_endpoint_calculated"]
