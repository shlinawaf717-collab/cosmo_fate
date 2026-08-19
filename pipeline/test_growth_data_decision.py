import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_wp6_growth_decision_requires_replacement_not_addition():
    decision = json.loads((ROOT / "plan/growth_data_decision.json").read_text())
    assert decision["decision"] == "GO_FOR_STAGED_IMPLEMENTATION_WITH_DR1_FS_BAO_REPLACEMENT"
    assert decision["data_change"]["remove"] == "DESI_DR2_all_BAO"
    assert decision["data_change"]["insert"] == "DESI_DR1_desi_fs_bao_all"
    assert "DR1_FS_BAO_plus_DR2_BAO" in decision["forbidden"]
    assert len(decision["dr1_code"]["commit"]) == 40
    assert decision["dr1_data"]["selected_file_count"] == 7
