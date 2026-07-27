from pathlib import Path

from pipeline.fit_wp3_truths import build_truth_config, parse_bestfit


def test_truth_config_fixes_wa_and_enforces_matter_dominance(tmp_path):
    info, config, output = build_truth_config("wap060", 0.6, 123, tmp_path)
    assert info["params"]["wa"] == 0.6
    assert info["params"]["w"]["prior"]["max"] < -0.6
    assert "prior" not in info
    assert info["sampler"]["minimize"] == {
        "ignore_prior": True,
        "best_of": 8,
        "seed": 123,
        "override_bobyqa": {"rhoend": 1e-5},
    }
    assert config == tmp_path / "wap060" / "fit.yaml"
    assert output == tmp_path / "wap060" / "fit"


def test_truth_config_retains_original_upper_bound_when_stricter(tmp_path):
    info, _, _ = build_truth_config("wam060", -0.6, 123, tmp_path)
    assert info["params"]["w"]["prior"]["max"] < 0.6


def test_parse_bestfit_table(tmp_path):
    path = tmp_path / "fit.bestfit.txt"
    path.write_text(
        "# weight minuslogpost ombh2 omegam H0 w Mb omch2 rdrag chi2\n"
        "1 10 0.022 0.3 70 -1.1 -19.3 0.12 147 20\n",
        encoding="utf-8",
    )
    row = parse_bestfit(path)
    assert row["w"] == -1.1
    assert row["chi2"] == 20
