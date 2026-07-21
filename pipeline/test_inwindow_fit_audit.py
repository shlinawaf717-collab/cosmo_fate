import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline import inwindow_fit_audit as audit


def test_gelman_rubin_uses_explicit_release_chains_without_sidecars():
    spec = audit.MODELS["CPL"]
    value = audit.gelman_rubin(spec["root"], 0.3, spec["sampled"])
    assert value == pytest.approx(0.006266847999499741, rel=1e-10)
