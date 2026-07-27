import json
from pathlib import Path

import numpy as np

from pipeline.monitor_wp4_f0 import (
    SAMPLED_PARAMETERS,
    collect_diagnostics,
    snapshot_chain,
)


def _write_chain(path: Path, seed: int, rows: int = 240) -> None:
    rng = np.random.default_rng(seed)
    names = ("weight", "minuslogpost", *SAMPLED_PARAMETERS)
    values = np.column_stack(
        (
            rng.integers(1, 4, size=rows),
            rng.normal(size=rows),
            rng.normal(size=(rows, len(SAMPLED_PARAMETERS))),
        )
    )
    with path.open("w", encoding="utf-8") as handle:
        handle.write("# " + " ".join(names) + "\n")
        np.savetxt(handle, values)


def test_snapshot_ignores_partial_final_record(tmp_path):
    path = tmp_path / "chain.txt"
    _write_chain(path, 1, rows=12)
    with path.open("ab") as handle:
        handle.write(b"1 2 3")
    snapshot = snapshot_chain(path)
    assert snapshot.data.shape[0] == 12
    assert snapshot.captured_bytes < snapshot.file_size_at_open


def test_monitor_is_non_authoritative_and_blinded(tmp_path):
    paths = []
    for index in range(4):
        path = tmp_path / f"chain-{index}.txt"
        _write_chain(path, index + 11)
        paths.append(path)
    result = collect_diagnostics(paths)
    assert result["decision_authority"] is False
    assert result["sampler_signal_capability"] is False
    assert set(result["rminus1"]["by_burn_fraction"]) == {"0.2", "0.5", "0.7"}
    assert set(result["ess"]["bulk_by_parameter"]) == set(SAMPLED_PARAMETERS)
    assert all(value is False for value in result["blinding"].values())
    rendered = json.dumps(result)
    for forbidden in ("posterior_mean", "best_fit_point", "fate_probability"):
        assert forbidden not in rendered
