import numpy as np

from pipeline.monitor_wp5_bin4 import SAMPLED_PARAMETERS, chain_paths, collect


def test_wp5_monitor_has_20_parameters_and_width_paths():
    assert len(SAMPLED_PARAMETERS) == 20
    paths = chain_paths("0p01")
    assert len(paths) == 4
    assert all("delta_0p01" in str(path) for path in paths)


def test_wp5_collect_uses_bin_gates_without_wp4_w_wa_keyerror(tmp_path):
    rng = np.random.default_rng(20260824)
    paths = []
    header = "# weight " + " ".join(SAMPLED_PARAMETERS) + "\n"
    for chain in range(4):
        path = tmp_path / f"chain{chain}.txt"
        draws = rng.normal(size=(80, len(SAMPLED_PARAMETERS)))
        draws += 0.02 * chain
        with path.open("w", encoding="utf-8") as handle:
            handle.write(header)
            for row in draws:
                handle.write("1 " + " ".join(f"{value:.17g}" for value in row) + "\n")
        paths.append(path)

    payload = collect(paths)

    assert payload["schema_version"] == "wp5-bin4-read-only-monitor-v2"
    assert set(payload["ess"]["bulk_by_parameter"]) == set(SAMPLED_PARAMETERS)
    assert set(payload["ess"]["tail_by_parameter"]) == set(SAMPLED_PARAMETERS)
    assert set(payload["candidate_gates"]) == {
        "rminus1_20d_burn_0p5_lt_0p01",
        "bulk_ess_all_wbins_gt_1000",
        "tail_ess_all_wbins_gt_400",
    }
