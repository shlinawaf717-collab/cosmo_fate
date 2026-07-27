import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WP7 = ROOT / "plan/wp7_analytic_prediction.json"
WP8_V1 = ROOT / "plan/wp8_future_continuation_protocol.json"
WP8_V2 = ROOT / "plan/wp8_future_continuation_amendment_v2.json"
AMENDMENTS = ROOT / "plan/PRD_EXTENSION_AMENDMENTS.md"


def test_v1_is_preserved_and_v2_is_an_append_only_correction():
    v1 = json.loads(WP8_V1.read_text(encoding="utf-8"))
    v2 = json.loads(WP8_V2.read_text(encoding="utf-8"))
    assert v1["schema_version"] == "wp8-future-continuation-v1"
    assert v2["parent_protocol"] == v1["schema_version"]
    assert v2["history_policy"].startswith("append")
    assert v2["retired_primary_endpoint"].startswith("thresholded robust")


def test_v2_uses_partial_identification_without_threshold():
    v2 = json.loads(WP8_V2.read_text(encoding="utf-8"))
    endpoint = v2["replacement_primary_endpoint"]
    assert "{RIP,heat}" in endpoint["categories"]
    assert endpoint["aggregate_threshold"] is None
    assert v2["interpretation"]["family_averaged_probability_allowed"] is False


def test_structural_c2_c3_controls_are_explicit():
    controls = json.loads(WP8_V2.read_text(encoding="utf-8"))[
        "structural_controls"
    ]
    assert controls["C2"]["P_RIP"] == 0.0
    assert controls["C3_unconditioned_measure"]["P_RIP"] == 0.5
    assert "selection-conditioned" in controls[
        "accepted_draw_composition_label"
    ]


def test_wp7_prediction_has_both_conditions_and_no_unconditional_half_claim():
    prediction = json.loads(WP7.read_text(encoding="utf-8"))["prediction"]
    assert "prior symmetry" in prediction["condition_1"]
    assert "negligible likelihood information" in prediction["condition_2"]
    assert "not evidence" in prediction["interpretation"]
    assert "## PRD-A007" in AMENDMENTS.read_text(encoding="utf-8")
