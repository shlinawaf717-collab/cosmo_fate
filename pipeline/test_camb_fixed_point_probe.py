from pathlib import Path

import numpy as np

from pipeline.camb_fixed_point_probe import (
    POINT_PARAMETERS,
    load_official_fixed_point,
)


def _chain(path: Path, minima: tuple[float, float]) -> None:
    names = ("weight", "minuslogpost", *POINT_PARAMETERS)
    data = np.ones((2, len(names)))
    data[:, 1] = minima
    data[:, 2:] += np.arange(len(POINT_PARAMETERS))
    with path.open("w", encoding="utf-8") as handle:
        handle.write("# " + " ".join(names) + "\n")
        np.savetxt(handle, data)


def test_load_official_fixed_point_finds_global_minimum(tmp_path):
    first = tmp_path / "first.txt"
    second = tmp_path / "second.txt"
    _chain(first, (4.0, 2.0))
    _chain(second, (3.0, 1.0))
    point, source = load_official_fixed_point([first, second])
    assert point["minuslogpost"] == 1.0
    assert source["path"] == str(second)
    assert source["zero_based_data_row"] == 1
