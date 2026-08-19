from pipeline.freeze_wp5_system import DELTA, WIDTHS


def test_wp5_frozen_seed_grid_is_unique_and_complete():
    seeds=[seed for values in WIDTHS.values() for seed in values]
    assert len(seeds)==12 and len(set(seeds))==12
    assert DELTA=={"0p005":.005,"0p01":.01,"0p02":.02}
