#!/usr/bin/env python3
r"""Generate paper/numbers.tex from pipeline JSON outputs.

Single source of truth for numbers quoted in the paper prose: every macro
below is computed and rounded HERE, from the same JSON artifacts that the
figure scripts consume. The paper \input{}s the result; hand-transcription
of these values into main.tex is thereby structurally impossible.

Motivation (editorial changelog 2026-07-08): the audit found one
hand-transcription defect (main text 3.04 vs authoritative 3.0347 -> 3.03,
figure correct) -- one number, two rounders. This script removes the second
rounder.

Usage: .venv/bin/python pipeline/gen_paper_numbers.py
Writes paper/numbers.tex and prints the macro table for review.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def load(rel):
    with open(os.path.join(ROOT, rel)) as f:
        return json.load(f)


ah = load("runs/phase3/fparam/ah.json")["KL_per_bin"]
null = load("runs/gate2/gate2_final_stats.json")
d0 = load("runs/phase2/fate/d0_cpl_p1.json")
prior_fate = load("runs/phase3/fparam/prior_fate_audit.json")["models"]
fate_cpl = load("runs/phase3/fparam/fate_cpl.json")
fate_jbp = load("runs/phase3/fparam/fate_jbp.json")
fate_ba = load("runs/phase3/fparam/fate_ba_a005.json")
fate_bin4 = load("runs/phase3/fparam/fate_bin4_a005.json")
fragility = load("runs/phase3/fragility_metrics.json")
inwindow = load("runs/phase3/fparam/inwindow_fit_audit.json")["models"]
nested_d0 = load("runs/phase2/nested_d0.json")
model_average = load("runs/phase3/fparam/model_average_audit.json")
nested_data = {
    name: load(f"runs/phase3/fdata/nested_{name.lower()}.json")
    for name in ("D1", "D2", "D3", "D4")
}


def nested_fate(row):
    return row.get("P_fate_weighted", row["P_fate_nested"])


def fragility_tex(axis, quantity):
    row = fragility[axis][quantity]
    if row["status"] == "structurally_unbounded_by_exact_zero":
        return r"\infty"
    if row["status"] == "finite_nested_sampling_zero_requires_limit_or_more_runs":
        return r"\mathrm{not\ identified}"
    return f"{row['log10_span_dex']:.3f}"

macros = [
    # Constraint horizon (Sec. VII E); bins w1..w4 = low-z .. high-z
    ("KLbinA", f"{ah['w1']:.2f}"),
    ("KLbinB", f"{ah['w2']:.2f}"),
    ("KLbinC", f"{ah['w3']:.2f}"),
    ("KLbinD", f"{ah['w4']:.2f}"),
    # Null calibration (Sec. VI)
    ("NullAcc", f"{null['accuracy'] * 100:.0f}"),
    ("NullKSp", f"{null['KS_p']:.2f}"),
    ("NullMean", f"{null['ph_mean']:.3f}"),
    ("NullMeanSE", f"{null['ph_mean_se']:.3f}"),
    ("RipNullMin", f"{null['P_RIP_null_min'] * 100:.2f}"),
    # D0+CPL+P1 baseline (abstract, Sec. V)
    ("DzeroDecayPct", f"{d0['DECAY']['P'] * 100:.2f}"),
    ("DzeroRipPct", f"{d0['RIP']['P'] * 100:.2f}"),
    ("DzeroRipErrPct", f"{d0['RIP']['mc_err'] * 100:.2f}"),
    ("NestedDzeroRipPct", f"{nested_fate(nested_d0)['RIP'] * 100:.3f}"),
    ("NestedDzeroRipSeedSdPct", f"{nested_d0['P_fate_between_seed_sd']['RIP'] * 100:.3f}"),
    ("NestedDzeroRipMinPct", f"{nested_d0['P_RIP_range'][0] * 100:.3f}"),
    ("NestedDzeroRipMaxPct", f"{nested_d0['P_RIP_range'][1] * 100:.3f}"),
    ("NestedDzeroOtherPct", f"{nested_fate(nested_d0)['OTHER'] * 100:.4f}"),
    ("NestedLnB", f"{nested_d0['lnB_CPL_over_LCDM']:.3f}"),
    ("NestedLnBSeedSd", f"{nested_d0['lnB_between_seed_sd']:.3f}"),
    ("NestedLnBMin", f"{nested_d0['lnB_range'][0]:.3f}"),
    ("NestedLnBMax", f"{nested_d0['lnB_range'][1]:.3f}"),
    ("NestedLnBInternalMin", f"{min(nested_d0['per_run_internal_lnB_errors']):.3f}"),
    ("NestedLnBInternalMax", f"{max(nested_d0['per_run_internal_lnB_errors']):.3f}"),
    ("ModelAvgLCDMPct", f"{model_average['posterior_P_LCDM'] * 100:.1f}"),
    ("ModelAvgCPLPct", f"{model_average['posterior_P_CPL'] * 100:.1f}"),
    ("ModelAvgHeatPct", f"{model_average['model_averaged_P_heat_death_compatible'] * 100:.2f}"),
    ("DOneNestedRipPct", f"{nested_fate(nested_data['D1'])['RIP'] * 100:.3f}"),
    ("DTwoNestedRipPct", f"{nested_fate(nested_data['D2'])['RIP'] * 100:.3f}"),
    ("DThreeNestedRipPct", f"{nested_fate(nested_data['D3'])['RIP'] * 100:.4f}"),
    ("DFourNestedRipPct", f"{nested_fate(nested_data['D4'])['RIP'] * 100:.3f}"),
    ("FDataNestedRipMinPct", f"{min(nested_fate(row)['RIP'] for row in [nested_d0, *nested_data.values()]) * 100:.4f}"),
    ("FDataNestedRipMaxPct", f"{max(nested_fate(row)['RIP'] for row in [nested_d0, *nested_data.values()]) * 100:.3f}"),
    # Grammar audit (A-005 exact finite-limit semantics)
    ("GrammarRipMinPct", f"{min(d['RIP']['P'] for d in (fate_cpl, fate_jbp, fate_ba, fate_bin4)) * 100:.2f}"),
    ("GrammarRipMaxPct", f"{max(d['RIP']['P'] for d in (fate_cpl, fate_jbp, fate_ba, fate_bin4)) * 100:.2f}"),
    ("GrammarHeatMinPct", f"{min(d['P_heat'] for d in (fate_cpl, fate_jbp, fate_ba, fate_bin4)) * 100:.2f}"),
    ("GrammarHeatMaxPct", f"{max(d['P_heat'] for d in (fate_cpl, fate_jbp, fate_ba, fate_bin4)) * 100:.2f}"),
    ("PriorRipMinPct", f"{min(prior_fate[m]['RIP']['P'] for m in ('CPL', 'JBP', 'BA', 'BIN4')) * 100:.1f}"),
    ("PriorRipMaxPct", f"{max(prior_fate[m]['RIP']['P'] for m in ('CPL', 'JBP', 'BA', 'BIN4')) * 100:.1f}"),
    ("BAPriorRipPct", f"{prior_fate['BA']['RIP']['P'] * 100:.1f}"),
    ("BINPriorRipPct", f"{prior_fate['BIN4']['RIP']['P'] * 100:.1f}"),
    ("BARipPct", f"{fate_ba['RIP']['P'] * 100:.2f}"),
    ("BADecayPct", f"{fate_ba['DECAY']['P'] * 100:.2f}"),
    ("BABoundaryPct", f"{fate_ba['boundary_fraction'] * 100:.2f}"),
    ("BINRipPct", f"{fate_bin4['RIP']['P'] * 100:.2f}"),
    ("BINDecayPct", f"{fate_bin4['DECAY']['P'] * 100:.2f}"),
    ("BINBoundaryPct", f"{fate_bin4['boundary_fraction'] * 100:.1f}"),
    ("FPriorRip", fragility_tex("F_prior", "P_RIP")),
    ("FPriorHeat", fragility_tex("F_prior", "P_heat")),
    ("FParamRip", fragility_tex("F_param", "P_RIP")),
    ("FParamHeat", fragility_tex("F_param", "P_heat")),
    ("FParamFitsRip", fragility_tex("F_param_fitted_four_diagnostic", "P_RIP")),
    ("FParamFitsHeat", fragility_tex("F_param_fitted_four_diagnostic", "P_heat")),
    ("FDataRip", fragility_tex("F_data", "P_RIP")),
    ("FDataHeat", fragility_tex("F_data", "P_heat")),
    ("RCPL", f"{inwindow['CPL']['Rminus1_multivariate_recomputed']:.4f}"),
    ("RJBP", f"{inwindow['JBP']['Rminus1_multivariate_recomputed']:.4f}"),
    ("RBA", f"{inwindow['BA']['Rminus1_multivariate_recomputed']:.4f}"),
    ("RBIN", f"{inwindow['BIN4']['Rminus1_multivariate_recomputed']:.4f}"),
]

out = os.path.join(ROOT, "paper", "numbers.tex")
with open(out, "w") as f:
    f.write("% GENERATED by pipeline/gen_paper_numbers.py -- do not edit.\n")
    f.write("% Sources: runs/phase3/fparam/ah.json,"
            " runs/gate2/gate2_final_stats.json,"
            " runs/phase2/fate/d0_cpl_p1.json,"
            " runs/phase3/fparam/{prior_fate_audit,fate_*,model_average_audit}.json\n")
    for name, val in macros:
        f.write(f"\\newcommand{{\\{name}}}{{{val}}}\n")

print(f"wrote {out}")
for name, val in macros:
    print(f"  \\{name:<16} = {val}")
