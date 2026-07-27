from pipeline.run_wp4_smoke import json_safe, parse_clik_checks


def test_parse_two_clik_self_checks():
    text = """
Checking likelihood '/x/tt.clik' on test data. got -11.6257 expected -11.6257 (diff 1.02746e-06)
Checking likelihood '/x/ee.clik' on test data. got -197.99 expected -197.99 (diff -4.1778e-08)
"""
    checks = parse_clik_checks(text)
    assert len(checks) == 2
    assert checks[0]["difference"] == 1.02746e-06
    assert checks[1]["difference"] == -4.1778e-08


def test_json_safe_replaces_nonfinite_checkpoint_values():
    assert json_safe({"Rminus1_last": float("inf")}) == {
        "Rminus1_last": "inf"
    }
