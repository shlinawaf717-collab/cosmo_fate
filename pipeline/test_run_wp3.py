import json

import pytest

from pipeline import run_wp3


def test_registered_case_count_and_seed_schedule():
    all_cases = run_wp3.requested_cases()
    asimov = run_wp3.requested_cases(asimov_only=True)
    noisy = run_wp3.requested_cases(noisy_only=True)
    assert len(all_cases) == 606
    assert len(asimov) == 6
    assert len(noisy) == 600
    assert asimov[0].seed == 311000
    assert asimov[-1].seed == 316000
    assert noisy[0].seed == 311001
    assert noisy[-1].seed == 316100
    assert len({case.seed for case in all_cases}) == 606


def test_case_modes_are_mutually_exclusive():
    with pytest.raises(ValueError, match="mutually exclusive"):
        run_wp3.requested_cases(asimov_only=True, noisy_only=True)


def test_completed_ledger_is_pair_keyed_and_ignores_errors(tmp_path):
    ledger = tmp_path / "results.jsonl"
    ledger.write_text(
        "\n".join(
            [
                json.dumps({"truth_id": "wam060", "k": 0}),
                json.dumps({"truth_id": "wap060", "k": 0, "error": "failed"}),
                "not json",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    assert run_wp3.completed_cases(ledger) == {("wam060", 0)}


def test_pending_is_truth_and_mock_pair_keyed(tmp_path):
    ledger = tmp_path / "results.jsonl"
    ledger.write_text(json.dumps({"truth_id": "wam060", "k": 0}) + "\n")
    cases = [
        run_wp3.Case("wam060", 1, -0.6, 0),
        run_wp3.Case("wap060", 6, 0.6, 0),
    ]
    assert run_wp3.pending_cases(cases, ledger) == [cases[1]]
