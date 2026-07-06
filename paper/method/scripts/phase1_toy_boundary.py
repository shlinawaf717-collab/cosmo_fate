#!/usr/bin/env python3
"""Phase 1 toy boundary experiment.

The calibrated one-dimensional case is:

    x_hat ~ Normal(theta0, sigma_data)
    theta | x_hat ~ Normal(x_hat, sigma_post)
    class A if theta > 0
    theta0 = 0

When sigma_post == sigma_data and theta0 == 0,
P(A | data) = Phi(x_hat / sigma_post) = Phi(Z), Z ~ Normal(0, 1),
so the repeated-experiment distribution is Uniform(0, 1).
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


def simulate(
    n_experiments: int,
    theta0: float,
    sigma_data: float,
    sigma_post: float,
    seed: int,
) -> np.ndarray:
    rng = np.random.default_rng(seed)
    x_hat = rng.normal(loc=theta0, scale=sigma_data, size=n_experiments)
    return stats.norm.cdf(x_hat / sigma_post)


def summarize(p_class: np.ndarray) -> dict[str, float | int | list[float]]:
    ks = stats.kstest(p_class, "uniform")
    quantiles = np.quantile(p_class, [0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99])
    return {
        "n": int(p_class.size),
        "mean": float(np.mean(p_class)),
        "variance": float(np.var(p_class, ddof=1)),
        "uniform_variance": 1.0 / 12.0,
        "direction_rate_P_gt_0p5": float(np.mean(p_class > 0.5)),
        "ks_D_vs_uniform": float(ks.statistic),
        "ks_p_vs_uniform": float(ks.pvalue),
        "quantiles_0p01_0p05_0p25_0p5_0p75_0p95_0p99": [
            float(x) for x in quantiles
        ],
    }


def make_figure(p_null: np.ndarray, p_shifted: dict[str, np.ndarray], out_path: Path) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(13.2, 4.1), constrained_layout=True)

    bins = np.linspace(0.0, 1.0, 31)
    axes[0].hist(
        p_null,
        bins=bins,
        density=True,
        color="#3568a8",
        alpha=0.82,
        edgecolor="white",
        linewidth=0.6,
    )
    axes[0].axhline(1.0, color="#242424", linewidth=1.4, linestyle="--", label="Uniform(0, 1)")
    axes[0].set_title("Boundary null")
    axes[0].set_xlabel("P(theta > 0 | data)")
    axes[0].set_ylabel("Density")
    axes[0].set_ylim(0, 1.35)
    axes[0].legend(frameon=False, loc="upper right")

    sorted_p = np.sort(p_null)
    ecdf = np.arange(1, sorted_p.size + 1) / sorted_p.size
    axes[1].plot(sorted_p, ecdf, color="#3568a8", linewidth=1.8, label="Simulation ECDF")
    axes[1].plot([0, 1], [0, 1], color="#242424", linewidth=1.2, linestyle="--", label="Uniform CDF")
    axes[1].set_title("Uniformity check")
    axes[1].set_xlabel("P(theta > 0 | data)")
    axes[1].set_ylabel("Cumulative probability")
    axes[1].set_xlim(0, 1)
    axes[1].set_ylim(0, 1)
    axes[1].legend(frameon=False, loc="lower right")

    colors = {
        "theta0 = 0.0 sigma": "#3568a8",
        "theta0 = 0.5 sigma": "#c47f2c",
        "theta0 = 1.0 sigma": "#2e7d58",
    }
    for label, values in p_shifted.items():
        axes[2].hist(
            values,
            bins=bins,
            density=True,
            histtype="step",
            linewidth=2.0,
            color=colors[label],
            label=label,
        )
    axes[2].set_title("Moving away from boundary")
    axes[2].set_xlabel("P(theta > 0 | data)")
    axes[2].set_ylabel("Density")
    axes[2].set_ylim(0, 3.7)
    axes[2].legend(frameon=False, loc="upper left")

    fig.suptitle("Phase 1 toy model: posterior class probability at a critical boundary", fontsize=13)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=220)
    plt.close(fig)


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_DIR.mkdir(parents=True, exist_ok=True)

    n = 200_000
    seed = 20260706
    sigma = 1.0

    p_null = simulate(n, theta0=0.0, sigma_data=sigma, sigma_post=sigma, seed=seed)
    p_shifted = {
        "theta0 = 0.0 sigma": p_null,
        "theta0 = 0.5 sigma": simulate(n, 0.5 * sigma, sigma, sigma, seed + 1),
        "theta0 = 1.0 sigma": simulate(n, 1.0 * sigma, sigma, sigma, seed + 2),
    }

    mismatch_wide = simulate(n, theta0=0.0, sigma_data=sigma, sigma_post=1.5 * sigma, seed=seed + 3)
    mismatch_tight = simulate(n, theta0=0.0, sigma_data=sigma, sigma_post=0.7 * sigma, seed=seed + 4)

    summary = {
        "model": {
            "x_hat": "Normal(theta0, sigma_data)",
            "posterior": "theta | x_hat ~ Normal(x_hat, sigma_post)",
            "class_A": "theta > 0",
        },
        "baseline": {
            "theta0": 0.0,
            "sigma_data": sigma,
            "sigma_post": sigma,
            "seed": seed,
            **summarize(p_null),
        },
        "off_boundary_theta0_0p5sigma": summarize(p_shifted["theta0 = 0.5 sigma"]),
        "off_boundary_theta0_1p0sigma": summarize(p_shifted["theta0 = 1.0 sigma"]),
        "posterior_width_mismatch_sigma_post_1p5sigma": summarize(mismatch_wide),
        "posterior_width_mismatch_sigma_post_0p7sigma": summarize(mismatch_tight),
        "analytic_result": (
            "If theta0=0 and sigma_post=sigma_data, then P(theta>0|data)=Phi(Z), "
            "Z~Normal(0,1), hence Uniform(0,1)."
        ),
    }

    stats_path = RESULT_DIR / "phase1_toy_boundary_stats.json"
    fig_path = FIG_DIR / "phase1_toy_boundary_uniformity.png"
    stats_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    make_figure(p_null, p_shifted, fig_path)

    print(f"wrote {stats_path}")
    print(f"wrote {fig_path}")
    print(json.dumps(summary["baseline"], indent=2))


if __name__ == "__main__":
    main()
