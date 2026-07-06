#!/usr/bin/env python3
"""Phase 4 null-calibration protocol.

This script turns the boundary toy setup into a reporting protocol:

1. generate null mocks under a boundary truth,
2. compute a raw posterior class probability for each mock,
3. compare an observed raw class probability with the null distribution,
4. report lower-tail, upper-tail, and two-sided calibrated p-values.

The observed values used here are synthetic examples. They illustrate the
protocol and do not make a claim about the real universe.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy import stats


ROOT = Path(__file__).resolve().parents[1]
FIG_DIR = ROOT / "figures"
RESULT_DIR = ROOT / "results"


def covariance(std_u: float, std_v: float, corr: float) -> np.ndarray:
    return np.array(
        [
            [std_u**2, corr * std_u * std_v],
            [corr * std_u * std_v, std_v**2],
        ]
    )


def simulate_boundary_null(n_mocks: int, seed: int) -> np.ndarray:
    """Use the Phase 2 w0-wa boundary analogue to generate null probabilities."""
    alpha = 1.2
    cov = covariance(std_u=0.070, std_v=0.260, corr=-0.72)
    b = np.array([alpha, 1.0])
    score_sigma = float(np.sqrt(b @ cov @ b))
    rng = np.random.default_rng(seed)
    xhat = rng.multivariate_normal([0.0, 0.0], cov, size=n_mocks)
    score_z = (xhat @ b) / score_sigma
    return stats.norm.cdf(score_z)


def calibrate(null: np.ndarray, observed: float) -> dict[str, float | int]:
    """Empirical calibration with plus-one smoothing.

    The plus-one rule prevents zero p-values with finite mocks and makes the
    minimum reportable tail probability 1/(N+1).
    """
    n = int(null.size)
    n_lower = int(np.sum(null <= observed))
    n_upper = int(np.sum(null >= observed))
    lower = (n_lower + 1.0) / (n + 1.0)
    upper = (n_upper + 1.0) / (n + 1.0)
    two_sided = min(1.0, 2.0 * min(lower, upper))
    return {
        "observed_raw_probability": float(observed),
        "n_mocks": n,
        "n_lower_or_equal": n_lower,
        "n_upper_or_equal": n_upper,
        "lower_tail_p": float(lower),
        "upper_tail_p": float(upper),
        "two_sided_p": float(two_sided),
        "minimum_reportable_tail_p": float(1.0 / (n + 1.0)),
    }


def make_flow_panel(ax) -> None:
    ax.axis("off")
    ax.set_title("Null-calibration protocol")
    items = [
        ("Observed posterior", "raw P(label | data)"),
        ("Classifier", "threshold label map"),
        ("Null mocks", "same pipeline under boundary truth"),
        ("Null distribution", "P(label | mock)"),
        ("Calibrated report", "tail depth + direction + evidence"),
    ]
    xs = [0.08, 0.08, 0.08, 0.08, 0.08]
    ys = [0.82, 0.64, 0.46, 0.28, 0.10]
    for i, ((title, body), x, y) in enumerate(zip(items, xs, ys)):
        ax.text(
            x,
            y,
            f"{title}\n{body}",
            transform=ax.transAxes,
            ha="left",
            va="center",
            fontsize=10,
            bbox=dict(boxstyle="round,pad=0.45", facecolor="#f7f7f7", edgecolor="#555555"),
        )
        if i < len(items) - 1:
            ax.annotate(
                "",
                xy=(0.45, y - 0.115),
                xytext=(0.45, y - 0.055),
                xycoords=ax.transAxes,
                arrowprops=dict(arrowstyle="->", linewidth=1.2, color="#555555"),
            )
    ax.text(
        0.59,
        0.74,
        "Raw class fraction\nis not the final claim.\nCompare it with\na null distribution.",
        transform=ax.transAxes,
        ha="left",
        va="center",
        fontsize=9,
        bbox=dict(boxstyle="round,pad=0.45", facecolor="#fff6df", edgecolor="#9a7a2f"),
    )


def make_figure(null100: np.ndarray, null_hi: np.ndarray, cases: dict, out_path: Path) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(12.8, 9.1), constrained_layout=True)
    ax0, ax1, ax2, ax3 = axes.ravel()

    make_flow_panel(ax0)

    bins = np.linspace(0.0, 1.0, 21)
    ax1.hist(
        null100,
        bins=bins,
        density=True,
        color="#3568a8",
        alpha=0.85,
        edgecolor="white",
        linewidth=0.7,
    )
    ax1.axhline(1.0, color="#222222", linestyle="--", linewidth=1.3, label="Uniform reference")
    markers = {
        "central_boundary_like": ("#555555", "central"),
        "low_tail_example": ("#b54e4a", "low-tail"),
        "high_tail_example": ("#2e8b57", "high-tail"),
    }
    for key, (color, label) in markers.items():
        obs = cases[key]["observed_raw_probability"]
        ax1.axvline(obs, color=color, linewidth=2.0, label=f"{label}: {obs:.3f}")
    ax1.set_title("Finite null mocks")
    ax1.set_xlabel("P(RIP-like | mock)")
    ax1.set_ylabel("Density")
    ax1.set_ylim(0, 1.75)
    ax1.legend(frameon=False, loc="upper center", fontsize=8)

    sorted_null = np.sort(null_hi)
    ecdf = np.arange(1, sorted_null.size + 1) / sorted_null.size
    ax2.plot(sorted_null, ecdf, color="#3568a8", linewidth=1.8, label="High-resolution null ECDF")
    ax2.plot([0, 1], [0, 1], color="#222222", linestyle="--", linewidth=1.2, label="Uniform CDF")
    for key, (color, label) in markers.items():
        obs = cases[key]["observed_raw_probability"]
        ax2.axvline(obs, color=color, linewidth=1.7)
        ax2.axhline(obs, color=color, linewidth=1.0, linestyle=":", alpha=0.7)
        ax2.text(obs + 0.012, min(0.96, obs + 0.04), label, color=color, fontsize=9)
    ax2.set_title("Tail depth from null CDF")
    ax2.set_xlabel("Observed raw class probability")
    ax2.set_ylabel("Null CDF")
    ax2.set_xlim(0, 1)
    ax2.set_ylim(0, 1)
    ax2.legend(frameon=False, loc="lower right", fontsize=8)

    labels = ["low-tail", "central", "high-tail"]
    lower = [
        cases["low_tail_example"]["lower_tail_p"],
        cases["central_boundary_like"]["lower_tail_p"],
        cases["high_tail_example"]["lower_tail_p"],
    ]
    upper = [
        cases["low_tail_example"]["upper_tail_p"],
        cases["central_boundary_like"]["upper_tail_p"],
        cases["high_tail_example"]["upper_tail_p"],
    ]
    x = np.arange(len(labels))
    width = 0.36
    ax3.bar(x - width / 2, lower, width, label="lower-tail p", color="#b54e4a", alpha=0.86)
    ax3.bar(x + width / 2, upper, width, label="upper-tail p", color="#2e8b57", alpha=0.86)
    ax3.axhline(1.0 / (len(null100) + 1.0), color="#222222", linestyle="--", linewidth=1.1, label="finite-mock floor")
    ax3.set_title("Calibrated tail reports")
    ax3.set_xticks(x)
    ax3.set_xticklabels(labels)
    ax3.set_ylabel("Empirical p-value")
    ax3.set_ylim(0, 1.05)
    ax3.legend(frameon=False, loc="upper center", fontsize=8)

    fig.suptitle("Phase 4: raw fate probability calibrated against a boundary null", fontsize=14)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=220)
    plt.close(fig)


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_DIR.mkdir(parents=True, exist_ok=True)

    seed = 20260709
    null100 = simulate_boundary_null(100, seed)
    null_hi = simulate_boundary_null(50_000, seed + 1)

    observed = {
        "central_boundary_like": 0.500,
        "low_tail_example": 0.018,
        "high_tail_example": 0.982,
    }
    cases = {key: calibrate(null100, value) for key, value in observed.items()}

    summary = {
        "protocol": [
            "Define a predeclared classifier C(theta).",
            "Compute raw P(label | observed data).",
            "Generate null mocks under the boundary or near-boundary null.",
            "Run the identical posterior and classifier pipeline on every mock.",
            "Compare the observed raw probability to the mock distribution.",
            "Report lower-tail, upper-tail, and two-sided calibrated p-values with finite-mock resolution.",
        ],
        "null_model": {
            "source": "Phase 2 w0-wa boundary analogue",
            "n_finite_mocks": int(null100.size),
            "seed": seed,
            "null_mean": float(np.mean(null100)),
            "null_variance": float(np.var(null100, ddof=1)),
            "minimum_reportable_tail_p": float(1.0 / (len(null100) + 1.0)),
            "ks_p_vs_uniform": float(stats.kstest(null100, "uniform").pvalue),
        },
        "synthetic_observed_cases": cases,
        "interpretation_rules": {
            "direction_layer": "Report whether raw P(label | data) is above or below 0.5, but do not treat this alone as discovery near a boundary.",
            "depth_layer": "Use the relevant null tail probability to describe how extreme the raw class probability is under the boundary null.",
            "finite_mock_rule": "Never report p=0; use plus-one smoothing and state the mock-count floor.",
            "not_a_cosmic_claim": "Synthetic observed values illustrate the calibration protocol only.",
        },
    }

    stats_path = RESULT_DIR / "phase4_null_calibration.json"
    fig_path = FIG_DIR / "phase4_null_calibration.png"
    stats_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    make_figure(null100, null_hi, cases, fig_path)

    print(f"wrote {stats_path}")
    print(f"wrote {fig_path}")
    print(json.dumps(summary["synthetic_observed_cases"], indent=2))


if __name__ == "__main__":
    main()
