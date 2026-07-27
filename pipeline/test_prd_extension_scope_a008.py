import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCOPE = ROOT / "plan/prd_extension_scope_amendment_a008.json"
PROTOCOL = ROOT / "plan/PRD_EXTENSION_PROTOCOL.md"
AMENDMENTS = ROOT / "plan/PRD_EXTENSION_AMENDMENTS.md"


def test_a008_separates_cmb_lensing_from_conditional_direct_growth():
    scope = json.loads(SCOPE.read_text(encoding="utf-8"))
    growth = scope["growth_scope"]
    assert scope["amendment_id"] == "PRD-A008"
    assert "CMB-lensing-sensitive" in scope["effective_question_2"]
    assert growth["cmb_lensing_is_in_wp4"] is True
    assert growth["direct_late_time_growth_is_promised_unconditionally"] is False
    assert growth["direct_late_time_growth_requires_wp6_data_gate"] is True


def test_historical_question_is_visible_with_append_only_correction():
    protocol = PROTOCOL.read_text(encoding="utf-8")
    amendments = AMENDMENTS.read_text(encoding="utf-8")
    assert "growth-sensitive analysis" in protocol
    assert "PRD-A008 prospectively corrects question 2" in protocol
    assert "## PRD-A008" in amendments
