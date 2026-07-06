#!/usr/bin/env python3
"""Phase 3 abstract fate-classifier framework.

This script does not implement the physical CPL fate classifier. It defines the
method-paper abstraction: continuous diagnostics are mapped to discrete fate
labels by priority-ordered threshold rules. The plot shows why posterior class
fractions are integrals of indicator functions, not ordinary continuous
parameter estimates.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap


ROOT = Path(__file__).resolve().parents[1]
FIG_DIR = ROOT / "figures"
RESULT_DIR = ROOT / "results"

LABELS = ["CRUNCH", "RIP", "DS", "DECAY", "OTHER"]
COLORS = {
    "CRUNCH": "#4d4d4d",
    "RIP": "#b54e4a",
    "DS": "#4575b4",
    "DECAY": "#2e8b57",
    "OTHER": "#b0b0b0",
}


def classify_margins(
    crunch_margin: np.ndarray,
    rip_margin: np.ndarray,
    ds_margin: np.ndarray,
    decay_margin: np.ndarray,
) -> np.ndarray:
    """Priority rule: CRUNCH > RIP > DS > DECAY > OTHER."""
    out = np.full(np.shape(rip_margin), "OTHER", dtype=object)
    out = np.where(decay_margin > 0, "DECAY", out)
    out = np.where(ds_margin > 0, "DS", out)
    out = np.where(rip_margin > 0, "RIP", out)
    out = np.where(crunch_margin > 0, "CRUNCH", out)
    return out


def labels_to_int(labels: np.ndarray) -> np.ndarray:
    mapping = {lab: i for i, lab in enumerate(LABELS)}
    return np.vectorize(mapping.get)(labels)


def fractions(labels: np.ndarray) -> dict[str, float]:
    n = labels.size
    return {lab: float(np.mean(labels == lab)) for lab in LABELS}


def ellipse(mu: np.ndarray, cov: np.ndarray, nsigma: float, n: int = 240) -> tuple[np.ndarray, np.ndarray]:
    vals, vecs = np.linalg.eigh(cov)
    order = np.argsort(vals)[::-1]
    vals = vals[order]
    vecs = vecs[:, order]
    angle = np.linspace(0.0, 2.0 * np.pi, n)
    circle = np.vstack((np.cos(angle), np.sin(angle)))
    pts = mu[:, None] + vecs @ (np.sqrt(vals)[:, None] * nsigma * circle)
    return pts[0], pts[1]


def make_decision_tree(ax) -> None:
    ax.axis("off")
    ax.set_title("Priority-ordered classifier")
    boxes = [
        (0.08, 0.78, "if crunch_margin > 0", "CRUNCH", COLORS["CRUNCH"]),
        (0.08, 0.58, "else if rip_margin > 0", "RIP", COLORS["RIP"]),
        (0.08, 0.38, "else if ds_margin > 0", "DS", COLORS["DS"]),
        (0.08, 0.18, "else if decay_margin > 0", "DECAY", COLORS["DECAY"]),
        (0.08, -0.02, "else", "OTHER", COLORS["OTHER"]),
    ]
    for i, (x, y, cond, lab, color) in enumerate(boxes):
        ax.text(
            x,
            y,
            cond,
            transform=ax.transAxes,
            fontsize=10,
            va="center",
            ha="left",
            bbox=dict(boxstyle="round,pad=0.35", facecolor="#f7f7f7", edgecolor="#555555"),
        )
        ax.text(
            0.70,
            y,
            lab,
            transform=ax.transAxes,
            fontsize=10,
            va="center",
            ha="center",
            color="white" if lab != "OTHER" else "#222222",
            bbox=dict(boxstyle="round,pad=0.35", facecolor=color, edgecolor=color),
        )
        if i < len(boxes) - 1:
            ax.annotate(
                "",
                xy=(0.50, y - 0.105),
                xytext=(0.50, y - 0.035),
                xycoords=ax.transAxes,
                arrowprops=dict(arrowstyle="->", color="#555555", linewidth=1.2),
            )
    ax.text(
        0.05,
        0.97,
        "Continuous diagnostics -> discrete label",
        transform=ax.transAxes,
        fontsize=10,
        fontweight="bold",
        va="top",
    )


def make_figure(summary: dict, out_path: Path) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(12.8, 9.1), constrained_layout=True)
    ax0, ax1, ax2, ax3 = axes.ravel()

    make_decision_tree(ax0)

    # Panel B: descriptor plane. x is RIP margin. y is a late-state descriptor.
    x = np.linspace(-1.2, 1.2, 360)
    y = np.linspace(-1.2, 1.2, 360)
    xx, yy = np.meshgrid(x, y)
    crunch = np.full_like(xx, -1.0)
    rip = xx
    ds = 0.18 - np.abs(yy)
    decay = -0.35 - yy
    labels = classify_margins(crunch, rip, ds, decay)
    cmap = ListedColormap([COLORS[lab] for lab in LABELS])
    ax1.imshow(
        labels_to_int(labels),
        origin="lower",
        extent=[x.min(), x.max(), y.min(), y.max()],
        aspect="auto",
        cmap=cmap,
        vmin=0,
        vmax=len(LABELS) - 1,
        alpha=0.88,
    )
    ax1.axvline(0, color="#222222", linewidth=1.4)
    ax1.axhline(-0.35, color="#222222", linewidth=1.0, linestyle="--")
    ax1.axhspan(-0.18, 0.18, xmin=0, xmax=0.5, color="none", ec="#222222", linestyle=":", linewidth=1.2)
    ax1.set_title("Example descriptor plane")
    ax1.set_xlabel("RIP margin")
    ax1.set_ylabel("Late-state descriptor")
    handles = [
        plt.Line2D([0], [0], marker="s", color="none", markerfacecolor=COLORS[lab], markersize=9, label=lab)
        for lab in ["RIP", "DS", "DECAY", "OTHER"]
    ]
    ax1.legend(handles=handles, frameon=False, loc="upper left", fontsize=8)

    # Panel C: posterior samples near a boundary.
    rng = np.random.default_rng(20260708)
    mean = np.array([-0.08, -0.48])
    cov = np.array([[0.23**2, 0.45 * 0.23 * 0.24], [0.45 * 0.23 * 0.24, 0.24**2]])
    samples = rng.multivariate_normal(mean, cov, size=7000)
    sx, sy = samples[:, 0], samples[:, 1]
    labs = classify_margins(
        np.full_like(sx, -1.0),
        sx,
        0.18 - np.abs(sy),
        -0.35 - sy,
    )
    for lab in ["RIP", "DS", "DECAY", "OTHER"]:
        sel = labs == lab
        ax2.scatter(sx[sel], sy[sel], s=5, alpha=0.35, color=COLORS[lab], label=f"{lab}: {np.mean(sel):.2f}")
    for nsigma, ls, lw in [(1.0, "-", 1.8), (2.0, "--", 1.2)]:
        ex, ey = ellipse(mean, cov, nsigma)
        ax2.plot(ex, ey, color="#222222", linestyle=ls, linewidth=lw)
    ax2.axvline(0, color="#222222", linewidth=1.2)
    ax2.axhline(-0.35, color="#222222", linewidth=1.0, linestyle="--")
    ax2.axhspan(-0.18, 0.18, color=COLORS["DS"], alpha=0.08)
    ax2.set_xlim(-1.2, 1.2)
    ax2.set_ylim(-1.2, 1.2)
    ax2.set_title("Posterior class fraction = mass in regions")
    ax2.set_xlabel("RIP margin")
    ax2.set_ylabel("Late-state descriptor")
    ax2.legend(frameon=False, loc="lower left", fontsize=8)
    summary["posterior_example_fractions"] = fractions(labs)

    # Panel D: continuous path and discontinuous labels.
    t = np.linspace(-1.0, 1.0, 600)
    path_x = t
    path_y = -0.55 + 0.10 * np.sin(2 * np.pi * (t + 0.2))
    path_labels = classify_margins(
        np.full_like(t, -1.0),
        path_x,
        0.18 - np.abs(path_y),
        -0.35 - path_y,
    )
    rip_indicator = (path_labels == "RIP").astype(float)
    decay_indicator = (path_labels == "DECAY").astype(float)
    ax3.plot(t, path_x, color="#444444", linewidth=1.4, label="continuous RIP margin")
    ax3.step(t, rip_indicator, where="mid", color=COLORS["RIP"], linewidth=2.0, label="1[label = RIP]")
    ax3.step(t, decay_indicator - 1.15, where="mid", color=COLORS["DECAY"], linewidth=2.0, label="1[label = DECAY] - 1.15")
    ax3.axvline(0, color="#222222", linestyle="--", linewidth=1.1)
    ax3.set_title("Continuous descriptors, discontinuous labels")
    ax3.set_xlabel("continuous path parameter")
    ax3.set_ylabel("value / shifted indicator")
    ax3.set_ylim(-1.25, 1.15)
    ax3.legend(frameon=False, loc="upper left", fontsize=8)
    summary["path_transition"] = {
        "rip_turns_on_at_margin": 0.0,
        "point_before_zero": str(path_labels[np.searchsorted(t, -0.01)]),
        "point_after_zero": str(path_labels[np.searchsorted(t, 0.01)]),
    }

    fig.suptitle("Phase 3: fate classifier as a thresholded boundary map", fontsize=14)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=220)
    plt.close(fig)


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_DIR.mkdir(parents=True, exist_ok=True)

    summary: dict = {
        "abstract_classifier": {
            "labels": LABELS,
            "priority": "CRUNCH > RIP > DS > DECAY > OTHER",
            "rule": [
                "if crunch_margin > 0: CRUNCH",
                "elif rip_margin > 0: RIP",
                "elif ds_margin > 0: DS",
                "elif decay_margin > 0: DECAY",
                "else: OTHER",
            ],
            "interpretation": (
                "Margins are continuous diagnostics. Labels are discontinuous "
                "threshold outputs. Posterior fate probabilities are integrals "
                "of label indicators over the posterior."
            ),
        }
    }

    fig_path = FIG_DIR / "phase3_classifier_framework.png"
    stats_path = RESULT_DIR / "phase3_classifier_framework.json"
    make_figure(summary, fig_path)
    stats_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"wrote {stats_path}")
    print(f"wrote {fig_path}")
    print(json.dumps(summary["posterior_example_fractions"], indent=2))


if __name__ == "__main__":
    main()
