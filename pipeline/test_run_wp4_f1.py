from pipeline.run_wp4_f1 import CHAIN_SEEDS, PROPOSAL, ROOT, build_chain_config


def test_f1_chain_configs_are_isolated_and_frozen():
    outputs = set()
    for ordinal, seed in enumerate(CHAIN_SEEDS, start=1):
        config = build_chain_config(ordinal, seed)
        assert config["sampler"]["mcmc"]["seed"] == seed
        assert config["sampler"]["mcmc"]["covmat"] == str(PROPOSAL.resolve())
        assert config["packages_path"] == str((ROOT / "data/cobaya_packages").resolve())
        outputs.add(config["output"])
    assert len(outputs) == 4
    assert CHAIN_SEEDS == (4511, 4512, 4513, 4514)


def test_f1_production_has_registered_target_and_no_fate_component():
    config = build_chain_config(1, CHAIN_SEEDS[0])
    assert "sn.pantheonplusshoes" in config["likelihood"]
    assert "sn.pantheonplus" not in config["likelihood"]
    assert "Mb" in config["params"]
    assert "matter_dom" in config["prior"]
    serialized = str(config["likelihood"]).lower()
    assert "fate" not in serialized
    assert "classifier" not in serialized
