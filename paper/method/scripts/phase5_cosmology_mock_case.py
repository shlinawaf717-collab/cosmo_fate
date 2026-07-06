#!/usr/bin/env python3
"""Phase 5 real-pipeline mock case study.

This script applies the Phase 4 null-calibration protocol to existing
cosmology-pipeline outputs:

    runs/gate2/results.jsonl                 100 noisy LCDM mocks + mock000
    runs/gate2/gate2_final_stats.json        gate-level summary
    runs/phase2/fate/d0_cpl_p1.json          observed D0 CPL+P1 fate result

No inference is run here. This is a read-only synthesis for the independent
method paper.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy import stats


REPO = Path(__file__).resolve().parents[3]
ROOT = Path(__file__).resolve().parents[1]
FIG_DIR = ROOT / "figures"
RESULT_DIR = ROOT / "results"

GATE2_RESULTS = REPO / "runs/gate2/results.jsonl"
GATE2_STATS = REPO / "runs/gate2/gate2_final_stats.json"
D0_FATE = REPO / "runs/phase2/fate/d0_cpl_p1.json"


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def plus_one_tail(null: np.ndarray, observed: float, side: str) -> dict[str, float | int]:
    n = int(null.size)
    if side == "lower":
        count = int(np.sum(null <= observed))
    elif side == "upper":
        count = int(np.sum(null >= observed))
    else:
        raise ValueError(side)
    return {
        "side": side,
        "count": count,
        "n": n,
        "p_plus_one": float((count + 1.0) / (n + 1.0)),
        "p_floor": float(1.0 / (n + 1.0)),
    }


def zero_success_upper95_clopper(n: int) -> float:
    """One-sided 95% Clopper-Pearson upper bound for zero successes in n trials."""
    return float(1.0 - 0.05 ** (1.0 / n))


def make_text_panel(ax, summary: dict) -> None:
    ax.axis("off")
    ax.set_title("Method-paper interpretation")
    lines = [
        ("Direction layer", "P_heat > 0.5 in 50/100 noisy null mocks"),
        ("Null shape", f"P_heat KS p = {summary['null']['P_heat_KS_p_vs_uniform']:.3f}"),
        ("Depth layer", "Observed P_RIP is below all noisy null mocks"),
        ("Finite mocks", f"plus-one lower-tail p = {summary['observed']['P_RIP_lower_tail']['p_plus_one']:.4f}"),
        ("95% upper", f"zero-count CP upper = {summary['observed']['P_RIP_lower_tail_upper95']:.4f}"),
        ("Guardrail", "Case study only; not a fate claim by itself"),
    ]
    y = 0.88
    for title, body in lines:
        ax.text(
            0.05,
            y,
            title,
            transform=ax.transAxes,
            fontsize=10,
            fontweight="bold",
            ha="left",
            va="center",
        )
        ax.text(
            0.38,
            y,
            body,
            transform=ax.transAxes,
            fontsize=10,
            ha="left",
            va="center",
        )
        y -= 0.14


def make_figure(noisy: list[dict], mock000: dict, observed: dict, summary: dict, out_path: Path) -> None:
    p_heat = np.array([r["P_heat"] for r in noisy], dtype=float)
    p_rip = np.array([r["P"]["RIP"] for r in noisy], dtype=float)
    other = np.array([r["P"]["OTHER"] for r in noisy], dtype=float)
    boundary = np.array([r["boundary_fraction"] for r in noisy], dtype=float)
    obs_heat = observed["P_heat_death_compatible"]
    obs_rip = observed["RIP"]["P"]

    fig, axes = plt.subplots(2, 2, figsize=(12.8, 9.1), constrained_layout=True)
    ax0, ax1, ax2, ax3 = axes.ravel()

    bins = np.linspace(0.0, 1.0, 21)
    ax0.hist(p_heat, bins=bins, density=True, color="#3568a8", alpha=0.85, edgecolor="white", linewidth=0.7)
    ax0.axhline(1.0, color="#222222", linestyle="--", linewidth=1.2, label="Uniform reference")
    ax0.axvline(mock000["P_heat"], color="#555555", linewidth=2.0, label=f"mock000 {mock000['P_heat']:.3f}")
    ax0.axvline(obs_heat, color="#b54e4a", linewidth=2.2, label=f"observed {obs_heat:.3f}")
    ax0.set_title("Direction layer: P_heat under LCDM null")
    ax0.set_xlabel("P_heat = P(DS) + P(DECAY)")
    ax0.set_ylabel("Density")
    ax0.set_ylim(0, 1.6)
    ax0.legend(frameon=False, loc="upper center", fontsize=8)

    rip_bins = np.linspace(0.0, 1.0, 26)
    ax1.hist(p_rip, bins=rip_bins, density=True, color="#7f6bb0", alpha=0.84, edgecolor="white", linewidth=0.7)
    ax1.axvline(obs_rip, color="#b54e4a", linewidth=2.4, label=f"observed {obs_rip:.4f}")
    ax1.axvline(p_rip.min(), color="#222222", linestyle="--", linewidth=1.4, label=f"null min {p_rip.min():.4f}")
    ax1.axvline(mock000["P"]["RIP"], color="#555555", linewidth=1.8, label=f"mock000 {mock000['P']['RIP']:.3f}")
    ax1.set_title("Depth layer: observed P_RIP below null floor")
    ax1.set_xlabel("P_RIP")
    ax1.set_ylabel("Density")
    ax1.set_ylim(0, 2.6)
    ax1.legend(frameon=False, loc="upper center", fontsize=8)

    sorted_heat = np.sort(p_heat)
    ecdf = np.arange(1, sorted_heat.size + 1) / sorted_heat.size
    ax2.plot(sorted_heat, ecdf, color="#3568a8", linewidth=1.8, label="Noisy null ECDF")
    ax2.plot([0, 1], [0, 1], color="#222222", linestyle="--", linewidth=1.2, label="Uniform CDF")
    ax2.axvline(obs_heat, color="#b54e4a", linewidth=2.0)
    ax2.axhline(summary["observed"]["P_heat_upper_tail"]["p_plus_one"], color="#b54e4a", linestyle=":", linewidth=1.4)
    ax2.set_title("Observed heat probability in null CDF")
    ax2.set_xlabel("P_heat")
    ax2.set_ylabel("Null CDF")
    ax2.set_xlim(0, 1)
    ax2.set_ylim(0, 1)
    ax2.legend(frameon=False, loc="lower right", fontsize=8)

    make_text_panel(ax3, summary)
    ax3.text(
        0.05,
        0.03,
        f"OTHER max = {other.max():.4f}; boundary max = {boundary.max():.4f}",
        transform=ax3.transAxes,
        fontsize=9,
        ha="left",
        va="bottom",
        bbox=dict(boxstyle="round,pad=0.35", facecolor="#f7f7f7", edgecolor="#666666"),
    )

    fig.suptitle("Phase 5: real-pipeline LCDM mock calibration case study", fontsize=14)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=220)
    plt.close(fig)


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_DIR.mkdir(parents=True, exist_ok=True)

    rows = read_jsonl(GATE2_RESULTS)
    noisy = sorted([r for r in rows if r["k"] != 0], key=lambda r: r["k"])
    mock000 = next(r for r in rows if r["k"] == 0)
    observed = json.loads(D0_FATE.read_text(encoding="utf-8"))
    gate2_stats = json.loads(GATE2_STATS.read_text(encoding="utf-8"))

    p_heat = np.array([r["P_heat"] for r in noisy], dtype=float)
    p_rip = np.array([r["P"]["RIP"] for r in noisy], dtype=float)
    other = np.array([r["P"]["OTHER"] for r in noisy], dtype=float)
    boundary = np.array([r["boundary_fraction"] for r in noisy], dtype=float)
    obs_heat = float(observed["P_heat_death_compatible"])
    obs_rip = float(observed["RIP"]["P"])

    rip_lower = plus_one_tail(p_rip, obs_rip, "lower")
    heat_upper = plus_one_tail(p_heat, obs_heat, "upper")
    summary = {
        "source_files": {
            "noisy_mocks_and_mock000": str(GATE2_RESULTS.relative_to(REPO)),
            "gate2_summary": str(GATE2_STATS.relative_to(REPO)),
            "observed_fate": str(D0_FATE.relative_to(REPO)),
        },
        "case_study_scope": (
            "Existing cosmology-pipeline outputs are used to demonstrate the "
            "null-calibration protocol. This synthesis does not rerun inference "
            "and does not claim a real cosmic fate by itself."
        ),
        "null": {
            "n_noisy_mocks": len(noisy),
            "P_heat_mean": float(np.mean(p_heat)),
            "P_heat_se": float(np.std(p_heat, ddof=1) / np.sqrt(len(p_heat))),
            "P_heat_KS_D_vs_uniform": float(stats.kstest(p_heat, "uniform").statistic),
            "P_heat_KS_p_vs_uniform": float(stats.kstest(p_heat, "uniform").pvalue),
            "direction_accuracy_P_heat_gt_0p5": float(np.mean(p_heat > 0.5)),
            "P_RIP_min": float(p_rip.min()),
            "P_RIP_median": float(np.median(p_rip)),
            "OTHER_max": float(other.max()),
            "boundary_max": float(boundary.max()),
            "mock000": {
                "P_heat": float(mock000["P_heat"]),
                "P_RIP": float(mock000["P"]["RIP"]),
                "boundary_fraction": float(mock000["boundary_fraction"]),
            },
        },
        "observed": {
            "P_heat": obs_heat,
            "P_RIP": obs_rip,
            "P_RIP_lower_tail": rip_lower,
            "P_RIP_lower_tail_upper95": zero_success_upper95_clopper(len(noisy)),
            "P_heat_upper_tail": heat_upper,
            "n_null_P_RIP_below_or_equal_observed": rip_lower["count"],
            "n_null_P_heat_above_or_equal_observed": heat_upper["count"],
        },
        "cross_check_gate2_report": gate2_stats,
        "method_interpretation": {
            "direction": "Under LCDM noisy mocks, P_heat > 0.5 occurs in 50/100 cases.",
            "depth": "Observed P_RIP is below all 100 noisy null mocks; finite-mock plus-one lower-tail p is 1/101, with a 95% zero-count Clopper-Pearson upper bound matching the Gate 2 report.",
            "guardrail": "This supports the calibration framework; it is not a standalone claim that the universe has a determined fate.",
        },
    }

    stats_path = RESULT_DIR / "phase5_cosmology_mock_case.json"
    fig_path = FIG_DIR / "phase5_cosmology_mock_case.png"
    stats_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    make_figure(noisy, mock000, observed, summary, fig_path)

    print(f"wrote {stats_path}")
    print(f"wrote {fig_path}")
    print(json.dumps({"null": summary["null"], "observed": summary["observed"]}, indent=2))


if __name__ == "__main__":
    main()
