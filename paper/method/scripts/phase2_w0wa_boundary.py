#!/usr/bin/env python3
"""Phase 2 two-dimensional w0-wa boundary toy model.

Coordinates are centered on Lambda-CDM:

    u = w0 + 1
    v = wa

The mock estimator and posterior are Gaussian in (u, v). A linear fate proxy

    s = alpha * u + v

defines a RIP-like side (s > 0) and DECAY-like side (s < 0). Lambda-CDM is at
(u, v) = (0, 0), exactly on the boundary. This is not a physical fate classifier;
it is a controlled two-dimensional boundary analogue for the method paper.
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


def ellipse(mu: np.ndarray, cov: np.ndarray, nsigma: float, n: int = 240) -> tuple[np.ndarray, np.ndarray]:
    vals, vecs = np.linalg.eigh(cov)
    order = np.argsort(vals)[::-1]
    vals = vals[order]
    vecs = vecs[:, order]
    angle = np.linspace(0.0, 2.0 * np.pi, n)
    circle = np.vstack((np.cos(angle), np.sin(angle)))
    pts = mu[:, None] + vecs @ (np.sqrt(vals)[:, None] * nsigma * circle)
    return pts[0], pts[1]


def pick_examples(p: np.ndarray, xhat: np.ndarray) -> list[dict[str, float | int | list[float]]]:
    targets = [0.08, 0.50, 0.92]
    labels = ["low RIP-like probability", "near boundary", "high RIP-like probability"]
    out = []
    used: set[int] = set()
    for target, label in zip(targets, labels):
        order = np.argsort(np.abs(p - target))
        idx = int(next(i for i in order if int(i) not in used))
        used.add(idx)
        out.append(
            {
                "label": label,
                "target": float(target),
                "index": idx,
                "u_hat": float(xhat[idx, 0]),
                "w0_hat": float(xhat[idx, 0] - 1.0),
                "wa_hat": float(xhat[idx, 1]),
                "P_RIP_like": float(p[idx]),
            }
        )
    return out


def make_figure(
    p_rip: np.ndarray,
    score_z: np.ndarray,
    examples: list[dict[str, float | int | list[float]]],
    cov_post: np.ndarray,
    alpha: float,
    out_path: Path,
) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(12.8, 9.2), constrained_layout=True)
    ax0, ax1, ax2, ax3 = axes.ravel()

    # Panel A: w0-wa plane and selected noisy posteriors.
    w0_grid = np.linspace(-1.28, -0.72, 300)
    boundary = -alpha * (w0_grid + 1.0)
    ax0.fill_between(w0_grid, boundary, 1.05, color="#dce9f6", alpha=0.9, label="RIP-like side")
    ax0.fill_between(w0_grid, -1.05, boundary, color="#f8e7d2", alpha=0.95, label="DECAY-like side")
    ax0.plot(w0_grid, boundary, color="#222222", linewidth=1.6, label="s = alpha(w0+1)+wa = 0")
    ax0.scatter([-1.0], [0.0], s=70, color="#111111", marker="*", zorder=5, label="Lambda-CDM truth")

    colors = ["#9a4f96", "#4f6db8", "#2e8b57"]
    for ex, color in zip(examples, colors):
        mu = np.array([float(ex["u_hat"]), float(ex["wa_hat"])])
        for nsigma, ls, lw in [(1.0, "-", 1.9), (2.0, "--", 1.2)]:
            eu, ev = ellipse(mu, cov_post, nsigma)
            ax0.plot(eu - 1.0, ev, color=color, linestyle=ls, linewidth=lw)
        ax0.scatter([float(ex["w0_hat"])], [float(ex["wa_hat"])], s=42, color=color, zorder=6)
        ax0.text(
            float(ex["w0_hat"]) + 0.01,
            float(ex["wa_hat"]) + 0.035,
            f"P={float(ex['P_RIP_like']):.2f}",
            fontsize=9,
            color=color,
        )
    ax0.set_title("Same Lambda-CDM truth, different noisy posteriors")
    ax0.set_xlabel("w0")
    ax0.set_ylabel("wa")
    ax0.set_xlim(-1.28, -0.72)
    ax0.set_ylim(-1.05, 1.05)
    ax0.legend(frameon=False, fontsize=8, loc="lower left")

    # Panel B: null distribution of posterior class probabilities.
    bins = np.linspace(0.0, 1.0, 31)
    ax1.hist(
        p_rip,
        bins=bins,
        density=True,
        color="#3568a8",
        edgecolor="white",
        linewidth=0.6,
        alpha=0.86,
    )
    ax1.axhline(1.0, color="#222222", linestyle="--", linewidth=1.4, label="Uniform(0, 1)")
    ax1.set_title("Null distribution of P(RIP-like)")
    ax1.set_xlabel("P(RIP-like | data)")
    ax1.set_ylabel("Density")
    ax1.set_ylim(0, 1.35)
    ax1.legend(frameon=False, loc="upper right")

    # Panel C: ECDF.
    sorted_p = np.sort(p_rip)
    ecdf = np.arange(1, sorted_p.size + 1) / sorted_p.size
    ax2.plot(sorted_p, ecdf, color="#3568a8", linewidth=1.8, label="Simulation ECDF")
    ax2.plot([0, 1], [0, 1], color="#222222", linestyle="--", linewidth=1.2, label="Uniform CDF")
    ax2.set_title("Uniformity check")
    ax2.set_xlabel("P(RIP-like | data)")
    ax2.set_ylabel("Cumulative probability")
    ax2.set_xlim(0, 1)
    ax2.set_ylim(0, 1)
    ax2.legend(frameon=False, loc="lower right")

    # Panel D: projected score drives the class probability.
    order = np.argsort(score_z)
    subsample = order[:: max(1, order.size // 4000)]
    ax3.scatter(score_z[subsample], p_rip[subsample], s=4, color="#3568a8", alpha=0.18, rasterized=True)
    zline = np.linspace(-3.2, 3.2, 400)
    ax3.plot(zline, stats.norm.cdf(zline), color="#222222", linewidth=1.5, label="Phi(projected score)")
    for ex, color in zip(examples, colors):
        z = stats.norm.ppf(float(ex["P_RIP_like"]))
        ax3.scatter([z], [float(ex["P_RIP_like"])], s=55, color=color, zorder=5)
    ax3.axhline(0.5, color="#777777", linestyle=":", linewidth=1.0)
    ax3.axvline(0.0, color="#777777", linestyle=":", linewidth=1.0)
    ax3.set_title("Two dimensions reduce to boundary-normal score")
    ax3.set_xlabel("score estimate / posterior score sigma")
    ax3.set_ylabel("P(RIP-like | data)")
    ax3.set_xlim(-3.2, 3.2)
    ax3.set_ylim(0, 1)
    ax3.legend(frameon=False, loc="lower right")

    fig.suptitle("Phase 2 toy model: w0-wa posterior crossing a fate boundary", fontsize=14)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=220)
    plt.close(fig)


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_DIR.mkdir(parents=True, exist_ok=True)

    n = 120_000
    seed = 20260707
    alpha = 1.2
    theta0 = np.array([0.0, 0.0])
    cov_data = covariance(std_u=0.070, std_v=0.260, corr=-0.72)
    cov_post = cov_data.copy()
    b = np.array([alpha, 1.0])
    score_sigma = float(np.sqrt(b @ cov_post @ b))

    rng = np.random.default_rng(seed)
    xhat = rng.multivariate_normal(theta0, cov_data, size=n)
    score_hat = xhat @ b
    score_z = score_hat / score_sigma
    p_rip = stats.norm.cdf(score_z)

    examples = pick_examples(p_rip, xhat)
    summary = {
        "model": {
            "coordinates": "u=w0+1, v=wa",
            "truth": "Lambda-CDM: u=0, v=0",
            "estimator": "xhat ~ Normal(theta0, Sigma_data)",
            "posterior": "theta | xhat ~ Normal(xhat, Sigma_post)",
            "fate_score": f"s = {alpha} * u + v",
            "class_RIP_like": "s > 0",
            "class_DECAY_like": "s < 0",
            "note": "This is a boundary analogue, not a physical fate classifier.",
        },
        "settings": {
            "n_experiments": n,
            "seed": seed,
            "alpha": alpha,
            "cov_data": cov_data.tolist(),
            "cov_post": cov_post.tolist(),
            "score_sigma": score_sigma,
        },
        "baseline": summarize(p_rip),
        "examples": examples,
        "analytic_result": (
            "For any linear boundary score s=b^T theta, if b^T theta0=0 and "
            "the posterior score variance matches the repeated-experiment "
            "score-estimator variance, then P(s>0|data)=Phi(Z), Z~N(0,1), "
            "hence Uniform(0,1)."
        ),
    }

    stats_path = RESULT_DIR / "phase2_w0wa_boundary_stats.json"
    fig_path = FIG_DIR / "phase2_w0wa_boundary.png"
    stats_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    make_figure(p_rip, score_z, examples, cov_post, alpha, fig_path)

    print(f"wrote {stats_path}")
    print(f"wrote {fig_path}")
    print(json.dumps(summary["baseline"], indent=2))


if __name__ == "__main__":
    main()
