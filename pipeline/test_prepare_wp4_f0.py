import yaml

from pipeline.prepare_wp4_f0 import (
    OFFICIAL_CONFIG,
    PUBLIC_ACT,
    PUBLIC_BAO,
    prepare_config,
)


def test_prepare_config_preserves_priors_and_normalizes_only_public_names():
    official = yaml.safe_load(OFFICIAL_CONFIG.read_text(encoding="utf-8"))
    prepared = prepare_config()
    assert prepared["params"] == official["params"]
    assert tuple(prepared["likelihood"]) == (
        PUBLIC_BAO,
        "sn.pantheonplus",
        "planck_2018_lowl.TT_clik",
        "planck_2018_lowl.EE_clik",
        "planck_NPIPE_highl_CamSpec.TTTEEE",
        PUBLIC_ACT,
    )
    assert prepared["likelihood"][PUBLIC_ACT]["version"] == "v1.2"
    assert prepared["theory"]["camb"]["extra_args"] == (
        official["theory"]["camb"]["extra_args"]
    )
    assert prepared["theory"]["camb"]["path"] == "global"


def test_prepare_config_removes_nersc_paths_and_freezes_seed():
    prepared = prepare_config()
    serialized = yaml.safe_dump(prepared)
    assert "/global/" not in serialized
    assert prepared["sampler"]["mcmc"]["seed"] == 4400
    assert prepared["sampler"]["mcmc"]["covmat"].endswith(
        "wp4_full_cmb/f0_proposal.covmat"
    )
    assert prepared["packages_path"].startswith("{YAML_ROOT}")
