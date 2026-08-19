from pipeline.audit_wp7_smoke import audit
from pipeline.wp7_truncation_preflight import build


def test_truncation_normalizations_are_estimable_without_fate():
    result = build()
    assert result["status"] == "PASS"
    assert all(row["normalization_estimate"] > 0 for row in result["settings"])
    assert not result["prior_fate_composition_calculated"]
    assert not result["fate_endpoint_calculated"]


def test_all_five_no_sampling_smokes_passed():
    result = audit()
    assert result["status"] == "PASS"
    assert len(result["settings"]) == 5
    assert not result["posterior_sampling_performed"]
    assert not result["production_authorized"]
