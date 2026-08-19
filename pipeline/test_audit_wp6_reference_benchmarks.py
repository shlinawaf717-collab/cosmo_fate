from pipeline.audit_wp6_reference_benchmarks import audit


def test_wp6_reference_failure_is_fail_closed():
    result = audit()
    assert result["status"] == "FAIL_HARD_REFERENCE_REPRODUCTION"
    assert not result["checks"]["official_cpl_map_gate"]
    assert not result["checks"]["public_corrected_loglike_interpretation"]
    assert result["production_authorized"] is False
    assert result["fate_calculation_authorized"] is False
