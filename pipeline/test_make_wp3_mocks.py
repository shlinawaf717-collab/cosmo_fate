from pipeline.fit_wp3_truths import TRUTH_SPECS


def test_wp3_registered_truth_grid_and_seeds_are_frozen():
    assert [row[0] for row in TRUTH_SPECS] == [
        "wam060",
        "wam030",
        "wam015",
        "wap015",
        "wap030",
        "wap060",
    ]
    assert [row[1] for row in TRUTH_SPECS] == [-0.6, -0.3, -0.15, 0.15, 0.3, 0.6]
    assert [row[2] for row in TRUTH_SPECS] == [
        2026072201,
        2026072202,
        2026072203,
        2026072204,
        2026072205,
        2026072206,
    ]
