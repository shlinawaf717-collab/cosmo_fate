from pipeline.evaluate_wp5_external_stop import gates


def test_wp5_external_gate_boundaries_are_strict():
    policy={"statistics":{"rminus1":{"primary_exclusive_maximum":.01,"sensitivity_exclusive_maximum":.02},
            "ess":{"gated_parameters":["w1","w2","w3","w4"],"bulk_exclusive_minimum":1000,"tail_exclusive_minimum":400}}}
    diag={"rminus1":{"by_burn_fraction":{"0.2":.019,"0.5":.009,"0.7":.019}},
          "ess":{"bulk_by_parameter":{f"w{i}":1001 for i in range(1,5)},
                 "tail_by_parameter":{f"w{i}":401 for i in range(1,5)}}}
    assert all(gates(diag,policy).values())
    diag["rminus1"]["by_burn_fraction"]["0.5"] = .01
    assert gates(diag,policy)["rminus1_primary"] is False
