import yaml

from pipeline.build_wp4_f1_config import build_config, validate_config


def test_f1_changes_only_registered_target_elements():
    config = build_config()
    validate_config(config)
    assert "sn.pantheonplus" not in config["likelihood"]
    assert config["likelihood"]["sn.pantheonplusshoes"]["use_abs_mag"] is True
    assert config["params"]["Mb"]["prior"] == {"min": -20.0, "max": -18.0}
    assert "(w + wa) < 0" in config["prior"]["matter_dom"]


def test_f1_external_rule_cannot_be_preempted_by_builtin_thresholds():
    mcmc = build_config()["sampler"]["mcmc"]
    assert mcmc["Rminus1_stop"] == 1e-6
    assert mcmc["Rminus1_cl_stop"] == 1e-6
    assert "Mb" in mcmc["blocking"][-1][1]


def test_checked_in_config_is_generator_exact():
    from pipeline.build_wp4_f1_config import DEFAULT_OUTPUT

    checked_in = yaml.safe_load(DEFAULT_OUTPUT.read_text(encoding="utf-8"))
    assert checked_in == build_config()
