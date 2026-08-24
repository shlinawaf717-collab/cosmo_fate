from pipeline.audit_wp8_completion import build_audit


def test_frozen_wp8_release_recomputes_from_ledger():
    result = build_audit()
    assert result["status"] == "PASS"
    assert result["source"]["rows"] == 96658
    assert result["source"]["native_weight"] == 308657
    assert result["all_tau_cross_boundary_native_weight_fraction"] == 1.0
    assert all(result["gates"].values())
