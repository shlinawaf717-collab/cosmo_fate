import json
from pathlib import Path

import numpy as np
import pytest

from pipeline.build_wp4_f1_proposal import (
    F1ProposalError,
    proposal_from_tail_halves,
    validate_f0_closure,
)


def _write_chain(path: Path, offset: float) -> None:
    rng = np.random.default_rng(int(offset) + 4)
    rows = 80
    values = rng.normal(size=(rows, 3))
    values[:, 1] += offset
    with path.open("w", encoding="utf-8") as handle:
        handle.write("# weight minuslogpost x y\n")
        table = np.column_stack(
            (rng.integers(1, 4, size=rows), np.ones(rows), values[:, 1:])
        )
        np.savetxt(handle, table)


def test_proposal_uses_tail_halves_and_is_positive_definite(tmp_path):
    paths = []
    for index in range(4):
        path = tmp_path / f"c{index}.txt"
        _write_chain(path, float(index))
        paths.append(path)
    covariance, audit = proposal_from_tail_halves(
        paths, parameters=("x", "y")
    )
    np.linalg.cholesky(covariance)
    assert audit["status"] == "PASS"
    assert all(record["post_burn_rows"] == 40 for record in audit["chains"])
    assert audit["posterior_locations_reported"] is False


def test_closure_gate_rejects_nonfinal_audit(tmp_path):
    path = tmp_path / "audit.json"
    path.write_text(
        json.dumps(
            {
                "status": "COMMIT_TO_EXTERNAL_STOP",
                "post_termination_gates_pass": True,
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(F1ProposalError):
        validate_f0_closure(path)
