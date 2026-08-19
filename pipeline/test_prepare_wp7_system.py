from pipeline.freeze_wp7_system import freeze
from pipeline.prepare_wp7_sbc_configs import prepare


def test_wp7_real_data_plan_has_five_times_four_chains():
    plan = freeze()
    assert len(plan["chains"]) == 20
    assert {row["setting"] for row in plan["chains"]} == {"primary", "sig025", "sig100", "ell035", "ell140"}
    assert len({row["seed"] for row in plan["chains"]}) == 20
    assert not plan["posterior_or_fate_endpoint_read"]


def test_wp7_sbc_plan_has_fifty_times_two_chains():
    plan = prepare()
    assert len(plan["chains"]) == 100
    assert len({row["seed"] for row in plan["chains"]}) == 100
    assert not plan["sbc_rank_calculated"]
