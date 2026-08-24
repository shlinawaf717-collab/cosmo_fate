import gzip

import numpy as np

from pipeline.report_wp8 import _composition, _ledger_bytes, _replicate_audit


def test_source_ledger_is_deterministic_and_preserves_native_fields():
    source = {
        "chain": np.array([1, 2]),
        "retained_row": np.array([11, 22]),
        "weights": np.array([3, 4]),
        "nodes": np.array(
            [
                [-1.0, -1.0, -1.0, -0.9, -1.0, -1.0, -1.2],
                [-1.0, -1.0, -1.0, -1.1, -1.0, -1.0, -0.8],
            ]
        ),
    }
    first = _ledger_bytes(source, np.array([0.1, -0.2]))
    second = _ledger_bytes(source, np.array([0.1, -0.2]))
    assert first == second
    text = gzip.decompress(first).decode()
    assert text.splitlines()[0] == "chain,retained_row,weight,w1,s1,c0_winf"
    assert text.splitlines()[1].startswith("1,11,3,-0.90000000000000002")


def test_fate_composition_uses_native_weights_and_separate_boundary_flag():
    result = _composition(np.array([-1.2, -1.0, -0.8]), np.array([1, 2, 1]))
    assert result["fractions"]["RIP"] == 0.25
    assert result["fractions"]["DS"] == 0.5
    assert result["fractions"]["DECAY"] == 0.25
    assert result["fractions"]["heat"] == 0.75
    assert result["fractions"]["BOUNDARY"] == 0.5


def test_replicate_gate_uses_registered_floor_or_three_combined_mcse():
    template = {
        "fate_among_admissible": {
            "fractions": {"RIP": 0.5, "DS": 0.0, "DECAY": 0.5, "heat": 0.5}
        },
        "fate_mcse": {"RIP": 0.0016, "DS": 0.0, "DECAY": 0.0016, "heat": 0.0016},
    }
    close = {
        "fate_among_admissible": {
            "fractions": {"RIP": 0.503, "DS": 0.0, "DECAY": 0.497, "heat": 0.497}
        },
        "fate_mcse": template["fate_mcse"],
    }
    far = {
        "fate_among_admissible": {
            "fractions": {"RIP": 0.52, "DS": 0.0, "DECAY": 0.48, "heat": 0.48}
        },
        "fate_mcse": template["fate_mcse"],
    }
    assert _replicate_audit(template, close)["all_probabilities_pass"] is True
    assert _replicate_audit(template, far)["all_probabilities_pass"] is False
