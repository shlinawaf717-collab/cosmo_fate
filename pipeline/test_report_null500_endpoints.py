import json
from pathlib import Path

import pytest

from pipeline.report_null500_endpoints import (
    EndpointReportError,
    build_report,
    compute_endpoints,
)


ROOT = Path(__file__).resolve().parents[1]


def _row(k: int, rip: float, heat: float) -> dict:
    other = 0.0
    return {
        "k": k,
        "P": {
            "CRUNCH": 0.0,
            "RIP": rip,
            "DS": 0.0,
            "DECAY": heat,
            "OTHER": other,
        },
        "P_heat": heat,
        "boundary_fraction": 0.0,
    }


def test_lower_tail_is_inclusive_and_mock000_is_excluded():
    rows = [_row(0, 0.0, 0.0)]
    rows.extend(
        _row(k, 0.2 if k <= 2 else 0.8, 0.6 if k <= 264 else 0.4)
        for k in range(1, 501)
    )
    endpoints = compute_endpoints(rows, observed_p_rip=0.2)
    assert endpoints["primary_depth"]["K"] == 2
    assert endpoints["primary_depth"]["qualifying_mock_indices"] == [1, 2]
    assert endpoints["finite_simulation_lower_tail"]["p_plus_one"] == 3 / 501
    assert endpoints["direction"]["K"] == 264
    assert endpoints[
        "mock000_mechanism_diagnostic_excluded_from_null"
    ]["P_RIP"] == 0.0


def test_duplicate_index_is_rejected():
    rows = [_row(k, 0.5, 0.5) for k in range(501)]
    rows[-1]["k"] = 499
    with pytest.raises(EndpointReportError, match="unique k=0..500"):
        compute_endpoints(rows, observed_p_rip=0.2)


def test_frozen_campaign_regression():
    report = build_report()
    endpoints = report["endpoints"]
    assert report["status"] == "PASS"
    assert endpoints["primary_depth"]["K"] == 2
    assert endpoints["primary_depth"]["qualifying_mock_indices"] == [131, 421]
    assert endpoints["direction"]["K"] == 264
    assert endpoints["finite_simulation_lower_tail"]["p_plus_one"] == 3 / 501
    assert endpoints["primary_depth"]["minimum_null_P_RIP"] == pytest.approx(
        0.001662465812194991
    )
    assert endpoints["tail_probability_interval"]["interval"][1] == pytest.approx(
        0.014374078562200318,
    )
    assert len(
        report["inputs"]["results_ledger"]["sha256"]
    ) == 64


def test_output_schema_is_json_serializable():
    json.dumps(build_report(), allow_nan=False)
