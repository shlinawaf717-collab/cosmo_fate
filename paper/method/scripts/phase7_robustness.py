#!/usr/bin/env python3
"""Phase 7 robustness checks for the boundary-calibration method paper.

The goal is not to make every variant look uniform. The goal is to show which
changes preserve the boundary-null result and which changes correctly appear as
diagnostic failures: off-boundary truth, posterior-width mismatch, and limited
mock resolution.
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


def simulate_1d(
    n: int,
    theta0: float,
    threshold: float,
    sigma_data: float,
    sigma_post: float,
    seed: int,
) -> np.ndarray:
    rng = np.random.default_rng(seed)
    xhat = rng.normal(theta0, sigma_data, size=n)
    return stats.norm.cdf((xhat - threshold) / sigma_post)


def summarize(p: np.ndarray) -> dict[str, float | int | list[float]]:
    ks = stats.kstest(p, "uniform")
    return {
        "n": int(p.size),
        "mean": float(np.mean(p)),
        "variance": float(np.var(p, ddof=1)),
        "uniform_variance": 1.0 / 12.0,
        "direction_rate_P_gt_0p5": float(np.mean(p > 0.5)),
        "ks_D_vs_uniform": float(ks.statistic),
        "ks_p_vs_uniform": float(ks.pvalue),
        "quantiles_0p05_0p5_0p95": [float(x) for x in np.quantile(p, [0.05, 0.5, 0.95])],
    }


def pass_uniform(summary: dict[str, float | int | list[float]]) -> bool:
    return (
        abs(float(summary["mean"]) - 0.5) <= 0.02
        and abs(float(summary["variance"]) - 1.0 / 12.0) <= 0.02
        and abs(float(summary["direction_rate_P_gt_0p5"]) - 0.5) <= 0.02
        and float(summary["ks_p_vs_uniform"]) >= 0.01
    )


def curved_boundary(seed: int) -> np.ndarray:
    """Moderately curved two-dimensional boundary with truth on the boundary."""
    n_exp = 3000
    n_samp = 1400
    alpha = 1.2
    beta = 1.5
    cov = np.array([[0.05**2, -0.2 * 0.05 * 0.12], [-0.2 * 0.05 * 0.12, 0.12**2]])
    rng = np.random.default_rng(seed)
    xhat = rng.multivariate_normal([0.0, 0.0], cov, size=n_exp)
    eps = rng.multivariate_normal([0.0, 0.0], cov, size=(n_exp, n_samp))
    theta = xhat[:, None, :] + eps
    score = theta[:, :, 1] + alpha * theta[:, :, 0] + beta * theta[:, :, 0] ** 2
    return np.mean(score > 0, axis=1)


def finite_mock_resolution(observed: float) -> list[dict[str, float | int]]:
    rows = []
    for n in [25, 50, 100, 250, 500, 1000]:
        rows.append(
            {
                "n_mocks": n,
                "observed_probability": observed,
                "expected_count_below_observed_under_uniform": float(n * observed),
                "probability_of_zero_below_observed_under_uniform": float((1.0 - observed) ** n),
                "plus_one_floor": float(1.0 / (n + 1.0)),
            }
        )
    return rows


def make_figure(results: dict, out_path: Path) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(13.2, 9.0), constrained_layout=True)
    ax0, ax1, ax2, ax3 = axes.ravel()

    # Panel A: ECDFs for one-dimensional variants.
    for key, style in [
        ("calibrated_boundary", ("#3568a8", "-", "calibrated boundary")),
        ("shifted_threshold_truth_on_boundary", ("#2e8b57", "-", "shifted threshold, truth on boundary")),
        ("off_boundary_truth", ("#b54e4a", "-", "off-boundary truth")),
        ("posterior_too_wide", ("#7f6bb0", "--", "posterior too wide")),
        ("posterior_too_tight", ("#c47f2c", "--", "posterior too tight")),
    ]:
        p = np.array(results["one_dimensional"][key]["samples"])
        p_sorted = np.sort(p)
        ecdf = np.arange(1, p_sorted.size + 1) / p_sorted.size
        color, linestyle, label = style
        ax0.plot(p_sorted, ecdf, color=color, linestyle=linestyle, linewidth=1.5, label=label)
    ax0.plot([0, 1], [0, 1], color="#222222", linestyle=":", linewidth=1.3, label="Uniform CDF")
    ax0.set_title("One-dimensional robustness variants")
    ax0.set_xlabel("P(class | data)")
    ax0.set_ylabel("ECDF")
    ax0.set_xlim(0, 1)
    ax0.set_ylim(0, 1)
    ax0.legend(frameon=False, fontsize=7, loc="lower right")

    # Panel B: compact diagnostic bars.
    labels = []
    means = []
    variances = []
    pass_flags = []
    for key in [
        "calibrated_boundary",
        "shifted_threshold_truth_on_boundary",
        "off_boundary_truth",
        "posterior_too_wide",
        "posterior_too_tight",
    ]:
        s = results["one_dimensional"][key]["summary"]
        labels.append(results["one_dimensional"][key]["short_label"])
        means.append(float(s["mean"]))
        variances.append(float(s["variance"]))
        pass_flags.append(results["one_dimensional"][key]["uniform_pass"])
    x = np.arange(len(labels))
    ax1.bar(x - 0.18, means, width=0.34, color="#3568a8", label="mean")
    ax1.bar(x + 0.18, variances, width=0.34, color="#8c8c8c", label="variance")
    ax1.axhline(0.5, color="#3568a8", linestyle=":", linewidth=1.2)
    ax1.axhline(1.0 / 12.0, color="#555555", linestyle=":", linewidth=1.2)
    for i, ok in enumerate(pass_flags):
        label_y = max(means[i], variances[i]) + 0.035
        ax1.text(i, label_y, "pass" if ok else "diagnostic\nfailure", ha="center", va="bottom", fontsize=8)
    ax1.set_title("Uniform-null diagnostics")
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, rotation=20, ha="right")
    ax1.set_ylim(0, 0.75)
    ax1.legend(frameon=False, fontsize=8, loc="upper left", bbox_to_anchor=(0.0, 1.02), ncol=2)

    # Panel C: curved boundary result.
    p_curved = np.array(results["curved_boundary"]["samples"])
    ax2.hist(p_curved, bins=np.linspace(0, 1, 26), density=True, color="#4f6db8", alpha=0.85,
             edgecolor="white", linewidth=0.7)
    ax2.axhline(1.0, color="#222222", linestyle="--", linewidth=1.2, label="Uniform reference")
    ax2.set_title("Moderately curved boundary, truth on boundary")
    ax2.set_xlabel("P(class | data)")
    ax2.set_ylabel("Density")
    ax2.set_ylim(0, 1.45)
    ax2.legend(frameon=False, fontsize=8, loc="upper right")
    cs = results["curved_boundary"]["summary"]
    ax2.text(
        0.03,
        0.95,
        f"mean={float(cs['mean']):.3f}\nKS p={float(cs['ks_p_vs_uniform']):.3f}\nstatus={results['curved_boundary']['interpretation']}",
        transform=ax2.transAxes,
        va="top",
        ha="left",
        fontsize=9,
        bbox=dict(boxstyle="round,pad=0.35", facecolor="#f7f7f7", edgecolor="#666666"),
    )

    # Panel D: finite mock resolution.
    rows = results["finite_mock_resolution"]
    ns = np.array([r["n_mocks"] for r in rows], dtype=float)
    floors = np.array([r["plus_one_floor"] for r in rows], dtype=float)
    pzero = np.array([r["probability_of_zero_below_observed_under_uniform"] for r in rows], dtype=float)
    ax3.plot(ns, floors, marker="o", color="#b54e4a", label="plus-one p floor")
    ax3.plot(ns, pzero, marker="s", color="#2e8b57", label="Pr[zero below observed]")
    ax3.set_xscale("log")
    ax3.set_yscale("log")
    ax3.set_title("Finite-mock tail resolution for observed P=0.018")
    ax3.set_xlabel("number of null mocks")
    ax3.set_ylabel("probability")
    ax3.grid(True, which="both", linestyle=":", linewidth=0.7, alpha=0.6)
    ax3.legend(frameon=False, fontsize=8, loc="upper right")

    fig.suptitle("Phase 7: robustness checks for boundary calibration", fontsize=14)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=220)
    plt.close(fig)


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_DIR.mkdir(parents=True, exist_ok=True)

    n = 80_000
    seed = 20260710
    one_d_specs = {
        "calibrated_boundary": {
            "short_label": "calibrated",
            "theta0": 0.0,
            "threshold": 0.0,
            "sigma_data": 1.0,
            "sigma_post": 1.0,
            "expected": "uniform pass",
        },
        "shifted_threshold_truth_on_boundary": {
            "short_label": "shifted",
            "theta0": 0.4,
            "threshold": 0.4,
            "sigma_data": 1.0,
            "sigma_post": 1.0,
            "expected": "uniform pass; boundary location is arbitrary if truth is on it",
        },
        "off_boundary_truth": {
            "short_label": "off-boundary",
            "theta0": 0.5,
            "threshold": 0.0,
            "sigma_data": 1.0,
            "sigma_post": 1.0,
            "expected": "non-uniform; direction information is expected",
        },
        "posterior_too_wide": {
            "short_label": "too wide",
            "theta0": 0.0,
            "threshold": 0.0,
            "sigma_data": 1.0,
            "sigma_post": 1.5,
            "expected": "non-uniform; posterior class probabilities are under-confident",
        },
        "posterior_too_tight": {
            "short_label": "too tight",
            "theta0": 0.0,
            "threshold": 0.0,
            "sigma_data": 1.0,
            "sigma_post": 0.7,
            "expected": "non-uniform; posterior class probabilities are over-confident",
        },
    }

    one_d: dict = {}
    for i, (key, spec) in enumerate(one_d_specs.items()):
        p = simulate_1d(
            n=n,
            theta0=spec["theta0"],
            threshold=spec["threshold"],
            sigma_data=spec["sigma_data"],
            sigma_post=spec["sigma_post"],
            seed=seed + i,
        )
        s = summarize(p)
        one_d[key] = {
            **spec,
            "summary": s,
            "uniform_pass": pass_uniform(s),
            "samples": [float(x) for x in p[::80]],  # enough for plotting, not the full array
        }

    p_curved = curved_boundary(seed + 20)
    curved_summary = summarize(p_curved)
    curved_pass = pass_uniform(curved_summary)
    results = {
        "purpose": (
            "Robustness appendix for the method paper: identify which variants "
            "preserve boundary-null uniformity and which correctly trigger diagnostics."
        ),
        "one_dimensional": one_d,
        "curved_boundary": {
            "description": "Two-dimensional moderately curved boundary with truth on the boundary.",
            "summary": curved_summary,
            "uniform_pass": curved_pass,
            "interpretation": "near-uniform" if curved_pass else "curvature diagnostic",
            "samples": [float(x) for x in p_curved],
        },
        "finite_mock_resolution": finite_mock_resolution(observed=0.018),
        "pass_criteria": {
            "must_pass": [
                "calibrated_boundary",
                "shifted_threshold_truth_on_boundary",
            ],
            "expected_diagnostic_failures": [
                "off_boundary_truth",
                "posterior_too_wide",
                "posterior_too_tight",
            ],
            "curved_boundary": "should be near-uniform for moderate local curvature; strong curvature should be reported as a boundary-model diagnostic, not hidden.",
        },
    }

    stats_path = RESULT_DIR / "phase7_robustness.json"
    fig_path = FIG_DIR / "phase7_robustness.png"
    stats_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    make_figure(results, fig_path)

    compact = {
        "one_dimensional": {
            k: {
                "mean": v["summary"]["mean"],
                "variance": v["summary"]["variance"],
                "ks_p": v["summary"]["ks_p_vs_uniform"],
                "uniform_pass": v["uniform_pass"],
                "expected": v["expected"],
            }
            for k, v in one_d.items()
        },
        "curved_boundary": {
            "mean": curved_summary["mean"],
            "variance": curved_summary["variance"],
            "ks_p": curved_summary["ks_p_vs_uniform"],
            "uniform_pass": curved_pass,
        },
    }
    print(f"wrote {stats_path}")
    print(f"wrote {fig_path}")
    print(json.dumps(compact, indent=2))


if __name__ == "__main__":
    main()
