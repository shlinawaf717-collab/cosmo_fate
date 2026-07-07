"""Paper figures F1-F6 (vector PDF, no in-figure titles — APS style).
Run: .venv/bin/python pipeline/make_paper_figs.py

F1  runs/gate1/f1_gate1_vs_official.pdf       pipeline vs official DR2 contours
F2  runs/phase2/f2_d0_fate_partition.pdf      D0 posterior over fate partition
F3  runs/gate2/f3_null_histogram.pdf          null-calibration histogram
F4  runs/phase3/fdata/f4_loo_forest.pdf       leave-one-out forest (wa + P(RIP))
F5  runs/phase3/fparam/f5_grammar_fates.pdf   fate composition across w(a) grammars
F6  runs/phase3/fparam/f6_constraint_horizon.pdf  BIN4 KL(a) profile

Inputs: MCMC chains (weighted means/stds recomputed, 30% burn-in dropped) and
the frozen fate/result JSONs — no numbers are hand-entered except bin edges (§1).
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


def load_chains(pattern, params, burn=0.3):
    """Concatenate cobaya/getdist chain files -> (samples[N,k], weights[N])."""
    vals, wts = [], []
    for f in sorted(glob.glob(pattern)):
        if not re.search(r"\.\d+\.txt$", f):
            continue
        with open(f) as fh:
            cols = fh.readline().lstrip("#").split()
        data = np.loadtxt(f)
        data = data[int(burn * len(data)):]
        vals.append(np.column_stack([data[:, cols.index(p)] for p in params]))
        wts.append(data[:, cols.index("weight")])
    return np.concatenate(vals), np.concatenate(wts)


def fig1():
    from getdist import MCSamples, plots
    pars, labs = ["w", "wa"], [r"w_0", r"w_a"]
    s_off, w_off = load_chains(os.path.join(RUNS, "gate1", "official", "chain.*.txt"), pars)
    s_pip, w_pip = load_chains(os.path.join(RUNS, "gate1", "mc", "w0wa.*.txt"), pars)
    mc_off = MCSamples(samples=s_off, weights=w_off, names=pars, labels=labs,
                       label="DESI DR2 official (full CMB)")
    mc_pip = MCSamples(samples=s_pip, weights=w_pip, names=pars, labels=labs,
                       label="this pipeline (compressed CMB)")
    g = plots.get_single_plotter(width_inch=4.2)
    g.plot_2d([mc_off, mc_pip], "w", "wa", filled=[True, False],
              colors=["#c1443c", "#c1443c"], lws=[1, 1.6])
    ax = g.subplots[0, 0]
    ax.plot(-1.0, 0.0, "o", ms=7, mfc="none", mec="navy", mew=1.5, zorder=5)
    ax.axhline(0.0, color="0.75", lw=0.7, ls=":")
    ax.axvline(-1.0, color="0.75", lw=0.7, ls=":")
    g.add_legend(["DESI DR2 official (full CMB)", "this pipeline (compressed CMB)"],
                 legend_loc="lower left", fontsize=8)
    out = os.path.join(RUNS, "gate1", "f1_gate1_vs_official.pdf")
    g.export(out)
    print("wrote", out)


def fig2():
    from getdist import MCSamples, plots
    pars, labs = ["w", "wa"], [r"w_0", r"w_a"]
    s, w = load_chains(os.path.join(RUNS, "phase2", "mc", "d0.*.txt"), pars)
    mc = MCSamples(samples=s, weights=w, names=pars, labels=labs)
    g = plots.get_single_plotter(width_inch=4.2)
    g.plot_2d(mc, "w", "wa", filled=True, colors=["#4878a8"])
    ax = g.subplots[0, 0]
    ax.set_xlim(-1.06, -0.64)
    ax.set_ylim(-1.55, 0.18)
    ax.axhspan(0.0, 0.18, color="#c1443c", alpha=0.10, zorder=0)
    ax.axhspan(-1.55, 0.0, color="#6aa66a", alpha=0.08, zorder=0)
    ax.axhline(0.0, color="0.25", lw=1.2)
    ax.text(-0.68, 0.09, r"RIP region ($w_a>0$)", fontsize=8, color="#8c2f28",
            ha="right", va="center")
    ax.text(-0.68, -1.44, r"DECAY region ($w_a<0$)", fontsize=8, color="#3d6b3d",
            ha="right", va="center")
    ax.plot(-1.0, 0.0, "o", ms=7, mfc="none", mec="navy", mew=1.8, zorder=6)
    ax.annotate(r"$\Lambda$CDM", (-1.0, 0.0), textcoords="offset points",
                xytext=(8, 6), fontsize=9, color="navy")
    out = os.path.join(RUNS, "phase2", "f2_d0_fate_partition.pdf")
    g.export(out)
    print("wrote", out)


def fig3():
    rows = [json.loads(l) for l in open(os.path.join(RUNS, "gate2", "results.jsonl"))]
    mocks = [r["P_heat"] for r in rows if r["k"] > 0]
    m000 = [r["P_heat"] for r in rows if r["k"] == 0][0]
    with open(os.path.join(RUNS, "phase2", "fate", "d0_cpl_p1.json")) as fh:
        real = json.load(fh)["P_heat_death_compatible"]

    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    nbins = 20
    ax.hist(mocks, bins=np.linspace(0, 1, nbins + 1), color="#a8c4e0",
            edgecolor="white", label=r"100 mocks, $\Lambda$CDM truth")
    ax.axhline(len(mocks) / nbins, color="0.4", ls="--", lw=1,
               label="uniform expectation")
    ax.axvline(real, color="#c1443c", lw=2.5,
               label=f"real data (D0): {real:.3f}")
    ax.axvline(m000, color="0.15", ls=":", lw=2,
               label=f"zero-noise mock: {m000:.2f}")
    ax.set_xlabel(r"$P$(heat-death compatible) $= P(\mathrm{DS}) + P(\mathrm{DECAY})$")
    ax.set_ylabel("mocks per bin")
    ax.set_xlim(-0.02, 1.04)
    ax.legend(fontsize=8, loc="upper left")
    fig.tight_layout()
    out = os.path.join(RUNS, "gate2", "f3_null_histogram.pdf")
    fig.savefig(out)
    print("wrote", out, f"(n_mocks={len(mocks)})")


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

    fig.subplots_adjust(left=0.13, right=0.98, bottom=0.17, top=0.83, wspace=0.06)
    out = os.path.join(RUNS, "phase3", "fdata", "f4_loo_forest.pdf")
    fig.savefig(out)
    print("wrote", out)


def fig5():
    grammars = [
        ("CPL",  "fate_cpl.json"),
        ("JBP",  "fate_jbp.json"),
        ("BA",   "fate_ba_a003.json"),
        ("BIN4", "fate_bin4_a003.json"),
        ("GP",   "fate_gp.json"),
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
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for _, c in classes]
    ax.legend(handles, [n for n, _ in classes], loc="lower right",
              bbox_to_anchor=(1.0, 1.005), ncol=3, frameon=False, fontsize=8)
    fig.tight_layout(rect=(0, 0, 0.9, 1))
    out = os.path.join(RUNS, "phase3", "fparam", "f5_grammar_fates.pdf")
    fig.savefig(out)
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
    fig.tight_layout()
    out = os.path.join(RUNS, "phase3", "fparam", "f6_constraint_horizon.pdf")
    fig.savefig(out)
    print("wrote", out)


def figA():
    """Appendix boundary-calibration toy: reproduces phase-1 sampling exactly
    (default_rng(20260706), n=2e5) so the annotated stats match the JSON."""
    from scipy.stats import norm, kstest
    n, seed = 200_000, 20260706
    cases = [
        ("calibrated, truth on boundary",
         norm.cdf(np.random.default_rng(seed).normal(0.0, 1.0, n)), "#4878a8"),
        (r"truth off boundary by $0.5\sigma$",
         norm.cdf(np.random.default_rng(seed + 1).normal(0.5, 1.0, n)), "#c1443c"),
        (r"posterior too tight ($0.7\sigma$)",
         norm.cdf(np.random.default_rng(seed + 4).normal(0.0, 1.0, n) / 0.7), "#6aa66a"),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(9, 2.7), sharey=True)
    for ax, (label, p, color) in zip(axes, cases):
        ax.hist(p, bins=40, density=True, color=color, alpha=0.75)
        ax.axhline(1.0, color="0.25", ls="--", lw=1)
        ks = kstest(p, "uniform").pvalue
        ax.set_title(label, fontsize=9)
        ax.text(0.5, 0.06, f"mean {p.mean():.3f}\nvar {p.var():.4f}\nKS $p$ "
                + (f"= {ks:.2f}" if ks > 5e-3 else r"$< 10^{-3}$"),
                transform=ax.transAxes, ha="center", fontsize=8, color="0.25")
        ax.set_xlabel(r"$P(\mathrm{class}\,A\mid\hat{x})$")
        ax.set_xlim(0, 1)
    axes[0].set_ylabel("density")
    fig.tight_layout()
    figdir = os.path.join(ROOT, "paper", "figures")
    os.makedirs(figdir, exist_ok=True)
    out = os.path.join(figdir, "figA_boundary_toy.pdf")
    fig.savefig(out)
    print("wrote", out)


if __name__ == "__main__":
    fig1()
    fig2()
    fig3()
    fig4()
    fig5()
    fig6()
    figA()
