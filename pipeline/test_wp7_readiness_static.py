import json

from pipeline.audit_wp7_readiness import REAL_PLAN, SBC_PLAN


def test_frozen_wp7_plan_counts_and_no_authorization_yet():
    assert len(json.loads(REAL_PLAN.read_text())["chains"]) == 20
    assert len(json.loads(SBC_PLAN.read_text())["chains"]) == 100
