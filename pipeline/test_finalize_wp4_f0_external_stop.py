import os
from pathlib import Path

import pytest

from pipeline.finalize_wp4_f0_external_stop import (
    ExternalStopError,
    _atomic_json,
    _wait_for_exit,
    _wait_for_stopped,
)


def test_atomic_json_round_trip(tmp_path):
    path = tmp_path / "audit.json"
    _atomic_json(path, {"status": "TEST"})
    assert path.read_text(encoding="utf-8").endswith("\n")
    assert '"status": "TEST"' in path.read_text(encoding="utf-8")


def test_wait_for_exit_accepts_missing_process():
    assert _wait_for_exit([99999999], timeout=0.01) == []


def test_wait_for_stopped_rejects_missing_process():
    with pytest.raises(ExternalStopError):
        _wait_for_stopped([99999999], timeout=0.01)
