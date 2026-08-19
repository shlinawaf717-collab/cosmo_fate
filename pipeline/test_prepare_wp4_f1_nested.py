import math
from pathlib import Path

import pytest
import yaml

from pipeline.prepare_wp4_f1_nested import P1_AREAS, SEEDS, build_config, corrections


def _base():
    return yaml.safe_load((Path(__file__).parent / "wp4_f1.yaml").read_text())


def test_nested_p1_area_corrections_and_partition():
    corr = corrections()
    assert corr["cpl"] == pytest.approx(math.log(20 / 15.5))
    assert corr["rip"] == pytest.approx(math.log(2))
    assert corr["decay"] == pytest.approx(math.log(12 / 11.5))
    assert P1_AREAS["rip_p1"] + P1_AREAS["decay_p1"] == P1_AREAS["p1"]


def test_nested_configs_keep_full_targets_and_region_bounds(tmp_path: Path):
    kwargs = dict(seed=SEEDS[0], project_root=tmp_path, packages_path=tmp_path / "packages",
                  polychord_path=tmp_path / "pc", output_root=tmp_path / "out")
    full = build_config(_base(), "cpl", **kwargs)
    rip = build_config(_base(), "rip", **kwargs)
    decay = build_config(_base(), "decay", **kwargs)
    lcdm = build_config(_base(), "lcdm", **kwargs)
    assert full["sampler"]["polychord"]["nlive"] == 500
    assert rip["params"]["wa"]["prior"] == {"min": 0.0, "max": 2.0}
    assert decay["params"]["wa"]["prior"] == {"min": -3.0, "max": 0.0}
    assert lcdm["params"]["w"] == -1.0 and lcdm["params"]["wa"] == 0.0
    assert "prior" not in lcdm
