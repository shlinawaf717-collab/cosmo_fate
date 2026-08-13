import json
from pathlib import Path

import numpy as np

from pipeline.monitor_wp4_f1 import SAMPLED_PARAMETERS, collect_diagnostics


def _write_chain(path: Path, seed: int, rows: int = 240) -> None:
    rng = np.random.default_rng(seed)
    names = ("weight", "minuslogpost", *SAMPLED_PARAMETERS)
    values = np.column_stack((
        rng.integers(1, 4, size=rows), rng.normal(size=rows),
        rng.normal(size=(rows, len(SAMPLED_PARAMETERS))),
    ))
    with path.open("w", encoding="utf-8") as handle:
        handle.write("# " + " ".join(names) + "\n")
        np.savetxt(handle, values)


def test_f1_monitor_is_18d_non_authoritative_and_blinded(tmp_path):
    paths = []
    for index in range(4):
        path = tmp_path / f"chain-{index}.txt"
        _write_chain(path, index + 20)
        paths.append(path)
    result = collect_diagnostics(paths)
    assert result["decision_authority"] is False
    assert set(result["ess"]["bulk_by_parameter"]) == set(SAMPLED_PARAMETERS)
    assert "18 F1 sampled parameters" in result["rminus1"]["definition"]
    assert all(value is False for value in result["blinding"].values())
    rendered = json.dumps(result)
    for forbidden in ("posterior_mean", "best_fit_point", "fate_probability"):
        assert forbidden not in rendered
