import json

from pipeline.audit_wp6_smoke import audit
from pipeline.build_wp6_reference_benchmarks import BESTFIT_SHA256, prepare


def test_wp6_no_sampling_smoke_audit_passes():
    result = audit()
    assert result["status"] == "PASS"
    assert result["checks"]["posterior_sample_rows_zero"]
    assert not result["scientific_endpoint_generated"]


def test_wp6_reference_plan_is_frozen_before_evaluation():
    plan = prepare()
    assert plan["status"] == "FROZEN_BEFORE_REFERENCE_EVALUATION"
    assert plan["tests"]["official_cpl_map_point"]["source_sha256"] == BESTFIT_SHA256
    assert plan["tests"]["public_release_fixed_point"]["max_abs_delta_chi2"] == 0.10
    assert plan["posterior_sampling_authorized"] is False
