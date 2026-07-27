from pipeline.report_wp3_power import ORDER, build_report


def test_report_preserves_complete_registered_order():
    points = {}
    for i, truth_id in enumerate(ORDER):
        wa = (-0.6, -0.3, -0.15, 0.15, 0.3, 0.6)[i]
        rate = 0.8 + 0.01 * i
        points[truth_id] = {
            "wa": wa,
            "correct_direction": "heat_death_compatible" if wa < 0 else "RIP",
            "direction_power": {
                "rate": rate,
                "exact_binomial_95_interval": [rate - 0.1, rate + 0.1],
            },
            "one_sided_depth_power": {
                "rate": rate - 0.1,
                "exact_binomial_95_interval": [rate - 0.2, rate],
            },
            "false_sign_fraction": {
                "rate": 1 - rate,
                "exact_binomial_95_interval": [0.0, 0.3],
            },
            "correct_mass_distribution": {
                "median": rate,
                "central_68_interval": [rate - 0.1, rate + 0.1],
            },
            "asimov_correct_mass": rate,
        }
    audit = {
        "status": "PASS",
        "registered_power_endpoints": {
            "truth_points": points,
            "outer_direction_power_threshold": 0.8,
            "outer_points_pass": True,
            "positive_claim_scope": "outer alternatives only",
            "monotonicity_diagnostic": {
                "status": "NO_DISJOINT_INTERVAL_REVERSAL",
                "evidential_role": "coarse diagnostic only",
            },
        },
    }
    profiles = {
        truth_id: {
            "profile_chi2": 100.0 + i,
            "delta_chi2_from_best_registered_truth": float(i),
            "source": f"truths/{truth_id}/truth.json",
        }
        for i, truth_id in enumerate(ORDER)
    }
    report = build_report(audit, profiles)
    assert [row["truth_id"] for row in report["rows"]] == list(ORDER)
    assert report["outer_points_pass"] is True
    assert report["rows"][-1]["delta_chi2_from_best_registered_truth"] == 5.0
    assert "outer alternatives only" in report["positive_claim_scope"]
