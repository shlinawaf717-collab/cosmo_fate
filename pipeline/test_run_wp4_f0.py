from pipeline.run_wp4_f0 import (
    CHAIN_SEEDS,
    PROPOSAL,
    ROOT,
    build_chain_config,
)


def test_chain_configs_have_isolated_outputs_and_frozen_seeds():
    outputs = set()
    for ordinal, seed in enumerate(CHAIN_SEEDS, start=1):
        config = build_chain_config(ordinal, seed)
        assert config["sampler"]["mcmc"]["seed"] == seed
        assert config["sampler"]["mcmc"]["covmat"] == str(PROPOSAL.resolve())
        assert config["packages_path"] == str(
            (ROOT / "data/cobaya_packages").resolve()
        )
        outputs.add(config["output"])
    assert len(outputs) == len(CHAIN_SEEDS)


def test_production_does_not_add_fate_components():
    config = build_chain_config(1, CHAIN_SEEDS[0])
    serialized = str(config["likelihood"]).lower()
    assert "fate" not in serialized
    assert "classifier" not in serialized
