from pipeline.run_wp4_f1_smoke import build_report


def test_f1_smoke_fails_without_f1_specific_markers():
    report = build_report(0, "Test initialization successful")
    assert report["status"] == "FAIL"
    assert report["f1_log_markers"]["pantheonplusshoes_initialized"] is False
