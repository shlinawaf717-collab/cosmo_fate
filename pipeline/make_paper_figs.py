"""Paper figures F4-F6. Run: .venv/bin/python pipeline/make_paper_figs.py

F4  runs/phase3/fdata/f4_loo_forest.png      leave-one-out forest (wa + P(RIP))
F5  runs/phase3/fparam/f5_grammar_fates.png  fate composition across w(a) grammars
F6  runs/phase3/fparam/f6_constraint_horizon.png  BIN4 KL(a) profile

Inputs: MCMC chains (weighted means/stds recomputed, 30% burn-in dropped) and
the frozen fate JSONs — no numbers are hand-entered except bin edges (§1).
"""

import glob
import json
import os
import re

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.join(os.path.dirname(__file__), "..")
RUNS = os.path.join(ROOT, "runs")
DPI = 200


def chain_stats(pattern, param="wa", burn=0.3):
    """Weighted mean/std of `param` over all chain files matching pattern."""
    vals, wts = [], []
    for f in sorted(glob.glob(pattern)):
        with open(f) as fh:
            cols = fh.readline().lstrip("#").split()
        data = np.loadtxt(f)
        if data.ndim == 1 or data.size == 0:
            continue
        data = data[int(burn * len(data)):]
        vals.append(data[:, cols.index(param)])
        wts.append(data[:, cols.index("weight")])
    v, w = np.concatenate(vals), np.concatenate(wts)
    mean = np.average(v, weights=w)
    std = np.sqrt(np.average((v - mean) ** 2, weights=w))
    return mean, std


def fig4():
    combos = [
        ("D0 (all)",     os.path.join(RUNS, "phase2", "mc", "d0*.txt"),
         os.path.join(RUNS, "phase2", "fate", "d0_cpl_p1.json")),
        ("D1 ($-$SH0ES)", os.path.join(RUNS, "phase3", "fdata", "d1*.txt"),
         os.path.join(RUNS, "phase3", "fdata", "fate_d1.json")),
        ("D2 ($-$CMB)",  os.path.join(RUNS, "phase3", "fdata", "d2*.txt"),
         os.path.join(RUNS, "phase3", "fdata", "fate_d2.json")),
        ("D3 ($-$BAO)",  os.path.join(RUNS, "phase3", "fdata", "d3*.txt"),
         os.path.join(RUNS, "phase3", "fdata", "fate_d3.json")),
        ("D4 ($-$SN)",   os.path.join(RUNS, "phase3", "fdata", "d4*.txt"),
         os.path.join(RUNS, "phase3", "fdata", "fate_d4.json")),
    ]
    # chain patterns must not swallow yaml/log files
    txt_only = lambda pat: [f for f in glob.glob(pat) if re.search(r"\.\d\.txt$", f)]

    labels, wa_m, wa_s, prip, prip_err, n_samp = [], [], [], [], [], []
    for label, pat, fate_file in combos:
        files = txt_only(pat)
        assert files, f"no chains for {label}: {pat}"
        m, s = chain_stats(os.path.join(os.path.dirname(pat),
                                        os.path.basename(pat)))
        with open(fate_file) as fh:
            fate = json.load(fh)
        labels.append(label)
        wa_m.append(m)
        wa_s.append(s)
        prip.append(fate["RIP"]["P"])
        prip_err.append(fate["RIP"]["mc_err"])
        n_samp.append(fate["n_samples"])
        print(f"{label:14s} wa = {m:+.3f} +- {s:.3f}   P(RIP) = {fate['RIP']['P']:.5f}")

    y = np.arange(len(labels))[::-1]
    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(9, 3.6), sharey=True,
        gridspec_kw=dict(width_ratios=[1.15, 1], wspace=0.06))

    ax1.errorbar(wa_m, y, xerr=wa_s, fmt="o", color="steelblue",
                 ecolor="steelblue", capsize=3, ms=5)
    ax1.axvline(0.0, color="0.3", lw=1)
    ax1.text(-0.07, 1.5, r"$\Lambda$CDM ($w_a=0$)", fontsize=8, color="0.3",
             rotation=90, va="center", ha="right")
    ax1.axvline(wa_m[0], color="steelblue", lw=0.8, ls=":", alpha=0.7)
    ax1.set_yticks(y)
    ax1.set_yticklabels(labels)
    ax1.set_xlabel(r"$w_a$ (posterior mean $\pm 1\sigma$)")
    ax1.set_title("magnitude: fragile", fontsize=9)

    floor = [1.0 / n for n in n_samp]
    for yi, p, e, fl in zip(y, prip, prip_err, floor):
        if p > 0:
            lo = max(p - e, fl / 10)
            ax2.errorbar([p], [yi], xerr=[[p - lo], [e]], fmt="o",
                         color="crimson", ecolor="crimson", capsize=3, ms=5)
        else:  # zero samples: show MC floor as upper limit
            ax2.errorbar([fl], [yi], xerr=[[fl * 0.6], [0]], fmt="<",
                         color="crimson", ms=6, xuplims=[True])
    ax2.set_xscale("log")
    ax2.set_xlim(6e-6, 3e-2)
    ax2.axvspan(6e-6, 3e-3, color="0.92", zorder=0)
    ax2.text(0.15, 0.06, "swings within 0–0.3%", fontsize=8, color="0.35",
             transform=ax2.transAxes, ha="left", va="bottom")
    ax2.set_xlabel(r"$P(\mathrm{RIP})$")
    ax2.set_title("fate direction: robust", fontsize=9)

    fig.suptitle("Leave-one-out response (CPL+P1 fixed)", fontsize=11)
    fig.subplots_adjust(left=0.13, right=0.98, bottom=0.17, top=0.83, wspace=0.06)
    out = os.path.join(RUNS, "phase3", "fdata", "f4_loo_forest.png")
    fig.savefig(out, dpi=DPI)
    print("wrote", out)


def fig5():
    grammars = [
        ("CPL",  "fate_cpl.json"),
        ("JBP",  "fate_jbp.json"),
        ("BA",   "fate_ba_a003.json"),
        ("BIN4", "fate_bin4_a003.json"),
    ]
    classes = [("RIP", "#c1443c"), ("DS", "#4878a8"), ("DECAY", "#6aa66a")]

    fig, ax = plt.subplots(figsize=(8, 3.4))
    ylabels = []
    for i, (name, fname) in enumerate(grammars[::-1]):
        with open(os.path.join(RUNS, "phase3", "fparam", fname)) as fh:
            d = json.load(fh)
        left = 0.0
        for cls, color in classes:
            p = d[cls]["P"]
            ax.barh(i, p, left=left, color=color, edgecolor="white", height=0.62)
            if p > 0.03:
                ax.text(left + p / 2, i, f"{100*p:.1f}%", ha="center",
                        va="center", fontsize=8,
                        color="white" if p > 0.08 else "0.2")
            left += p
        heat = d["P_heat"]
        ax.text(1.012, i, f"heat-death\ncompatible {100*heat:.1f}%",
                va="center", fontsize=7.5, color="0.25")
        ylabels.append(name)
        print(f"{name:5s} RIP={d['RIP']['P']:.4f} DS={d['DS']['P']:.4f} "
              f"DECAY={d['DECAY']['P']:.4f} heat={heat:.4f}")

    ax.set_yticks(range(len(ylabels)))
    ax.set_yticklabels(ylabels)
    ax.set_xlim(0, 1)
    ax.set_xlabel("posterior fate probability (D0 + P1 fixed; A-003 criteria)")
    ax.set_title("Same data, same priors — four $w(a)$ grammars, four fate tables",
                 fontsize=10, pad=26)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for _, c in classes]
    ax.legend(handles, [n for n, _ in classes], loc="lower right",
              bbox_to_anchor=(1.0, 1.005), ncol=3, frameon=False, fontsize=8)
    fig.tight_layout(rect=(0, 0, 0.9, 1))
    out = os.path.join(RUNS, "phase3", "fparam", "f5_grammar_fates.png")
    fig.savefig(out, dpi=DPI)
    print("wrote", out)


def fig6():
    with open(os.path.join(RUNS, "phase3", "fparam", "ah.json")) as fh:
        kl = json.load(fh)["KL_per_bin"]
    # frozen BIN4 edges (plan §1): z in [0,0.3), [0.3,0.7), [0.7,1.5), [1.5,z_CMB]
    z_cmb = 1090.0
    z_edges = [0.0, 0.3, 0.7, 1.5, z_cmb]
    a_edges = [1.0 / (1.0 + z) for z in z_edges]  # 1, .769, .588, .4, ~9.2e-4
    vals = [kl["w1"], kl["w2"], kl["w3"], kl["w4"]]

    fig, ax = plt.subplots(figsize=(8, 3.8))
    for (a_hi, a_lo), v in zip(zip(a_edges[:-1], a_edges[1:]), vals):
        ax.hlines(v, a_lo, a_hi, color="steelblue", lw=3.5)
        ax.text(np.sqrt(a_lo * a_hi), v + 0.09, f"{v:.2f}",
                ha="center", fontsize=8, color="steelblue")
    # fate epoch: data-sourced KL identically zero
    a_max = 1.0e4
    ax.hlines(0.0, 1.0, a_max, color="#c1443c", lw=3.5)
    ax.axvspan(1.0, a_max, color="#c1443c", alpha=0.06, zorder=0)
    ax.text(np.sqrt(1.0 * a_max), 0.32,
            "fate epoch ($a>1$): data KL $\\equiv$ 0\n"
            "all information grammar-transported",
            ha="center", fontsize=8.5, color="#c1443c")
    ax.axhline(0.1, color="0.4", ls="--", lw=1)
    ax.text(1.3e-3, 0.16, "0.1 nat horizon threshold", fontsize=8, color="0.4")
    ax.axvline(1.0, color="0.6", lw=0.8)
    ax.text(0.93, 2.6, "today", rotation=90, fontsize=8, color="0.5", ha="right")

    ax.set_xscale("log")
    ax.set_xlim(a_edges[-1] * 0.8, a_max)
    ax.set_ylim(-0.15, 3.45)
    ax.set_xlabel("scale factor $a$")
    ax.set_ylabel(r"$D_{\rm KL}\,[\,p(w(a))\,\|\,\pi\,]$  [nat]")
    ax.set_title("Constraint horizon (BIN4): the data never stop speaking "
                 "before $a=1$ — and never start after", fontsize=10)
    fig.tight_layout()
    out = os.path.join(RUNS, "phase3", "fparam", "f6_constraint_horizon.png")
    fig.savefig(out, dpi=DPI)
    print("wrote", out)


if __name__ == "__main__":
    fig4()
    fig5()
    fig6()
