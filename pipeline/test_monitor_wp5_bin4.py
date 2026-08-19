from pipeline.monitor_wp5_bin4 import SAMPLED_PARAMETERS, chain_paths


def test_wp5_monitor_has_20_parameters_and_width_paths():
    assert len(SAMPLED_PARAMETERS) == 20
    paths = chain_paths("0p01")
    assert len(paths) == 4
    assert all("delta_0p01" in str(path) for path in paths)
