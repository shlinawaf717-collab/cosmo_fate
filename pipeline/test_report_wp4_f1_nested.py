import math

import pytest
from scipy.special import logsumexp

from pipeline.prepare_wp4_f1_nested import P1_AREAS


def test_stratified_evidence_recombines_conditional_regions():
    rip, decay = -10.0, -2.0
    total = logsumexp([
        math.log(P1_AREAS["rip_p1"] / P1_AREAS["p1"]) + rip,
        math.log(P1_AREAS["decay_p1"] / P1_AREAS["p1"]) + decay,
    ])
    p = math.exp(math.log(P1_AREAS["rip_p1"] / P1_AREAS["p1"]) + rip - total)
    direct = (4 * math.exp(rip)) / (4 * math.exp(rip) + 11.5 * math.exp(decay))
    assert p == pytest.approx(direct)
