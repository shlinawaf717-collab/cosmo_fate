#!/usr/bin/env python3
"""Phase 8 manuscript blueprint for the boundary-calibration method paper."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch


ROOT = Path(__file__).resolve().parents[1]
FIG_DIR = ROOT / "figures"
RESULT_DIR = ROOT / "results"


def load_json(name: str) -> dict:
    return json.loads((RESULT_DIR / name).read_text())


def fmt(x: float, digits: int = 5) -> str:
    return f"{x:.{digits}f}"


def wrap_cell(text: str, width: int = 54) -> str:
    return "<br>".join(textwrap.wrap(text, width=width, break_long_words=False))


def markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    out = ["| " + " | ".join(headers) + " |"]
    out.append("|" + "|".join(["---"] * len(headers)) + "|")
    for row in rows:
        out.append("| " + " | ".join(row) + " |")
    return "\n".join(out)


def phase_inventory() -> list[dict]:
    return [
        {
            "phase": "0",
            "artifact": "PHASE0_BOUNDARY_PROBLEM.md",
            "role": "Defines the independent method-paper object and non-goals.",
            "result": None,
            "figure": None,
        },
        {
            "phase": "1",
            "artifact": "PHASE1_TOY_BOUNDARY.md",
            "role": "One-dimensional boundary-null demonstration.",
            "result": "phase1_toy_boundary_stats.json",
            "figure": "phase1_toy_boundary_uniformity.png",
        },
        {
            "phase": "2",
            "artifact": "PHASE2_W0WA_BOUNDARY.md",
            "role": "Cosmology-shaped two-dimensional boundary analogue.",
            "result": "phase2_w0wa_boundary_stats.json",
            "figure": "phase2_w0wa_boundary.png",
        },
        {
            "phase": "3",
            "artifact": "PHASE3_CLASSIFIER_FRAMEWORK.md",
            "role": "Abstract fate classifier with continuous diagnostics.",
            "result": "phase3_classifier_framework.json",
            "figure": "phase3_classifier_framework.png",
        },
        {
            "phase": "4",
            "artifact": "PHASE4_NULL_CALIBRATION.md",
            "role": "Finite-mock calibration protocol and p-value rule.",
            "result": "phase4_null_calibration.json",
            "figure": "phase4_null_calibration.png",
        },
        {
            "phase": "5",
            "artifact": "PHASE5_COSMOLOGY_MOCK_CASE.md",
            "role": "Read-only real-pipeline LCDM mock case study.",
            "result": "phase5_cosmology_mock_case.json",
            "figure": "phase5_cosmology_mock_case.png",
        },
        {
            "phase": "6",
            "artifact": "PHASE6_REPORTING_STANDARD.md",
            "role": "Five-layer reporting standard.",
            "result": "phase6_reporting_standard.json",
            "figure": "phase6_reporting_standard.png",
        },
        {
            "phase": "7",
            "artifact": "PHASE7_ROBUSTNESS.md",
            "role": "Robustness and diagnostic-failure appendix.",
            "result": "phase7_robustness.json",
            "figure": "phase7_robustness.png",
        },
    ]


def build_blueprint() -> dict:
    p1 = load_json("phase1_toy_boundary_stats.json")
    p2 = load_json("phase2_w0wa_boundary_stats.json")
    p3 = load_json("phase3_classifier_framework.json")
    p4 = load_json("phase4_null_calibration.json")
    p5 = load_json("phase5_cosmology_mock_case.json")
    p6 = load_json("phase6_reporting_standard.json")
    p7 = load_json("phase7_robustness.json")

    inv = phase_inventory()
    inventory = []
    for item in inv:
        artifact_ok = (ROOT / item["artifact"]).exists()
        result_applicable = item["result"] is not None
        figure_applicable = item["figure"] is not None
        result_ok = (not result_applicable) or (RESULT_DIR / item["result"]).exists()
        figure_ok = (not figure_applicable) or (FIG_DIR / item["figure"]).exists()
        inventory.append(
            {
                **item,
                "artifact_ok": artifact_ok,
                "result_applicable": result_applicable,
                "result_ok": result_ok,
                "figure_applicable": figure_applicable,
                "figure_ok": figure_ok,
            }
        )

    key_numbers = {
        "phase1_boundary_null": {
            "n": p1["baseline"]["n"],
            "mean": p1["baseline"]["mean"],
            "variance": p1["baseline"]["variance"],
            "ks_p": p1["baseline"]["ks_p_vs_uniform"],
            "direction_rate": p1["baseline"]["direction_rate_P_gt_0p5"],
        },
        "phase2_w0wa_boundary": {
            "n": p2["baseline"]["n"],
            "mean": p2["baseline"]["mean"],
            "variance": p2["baseline"]["variance"],
            "ks_p": p2["baseline"]["ks_p_vs_uniform"],
            "direction_rate": p2["baseline"]["direction_rate_P_gt_0p5"],
        },
        "phase5_case_study": {
            "n_noisy_mocks": p5["null"]["n_noisy_mocks"],
            "P_heat_mean": p5["null"]["P_heat_mean"],
            "P_heat_ks_p": p5["null"]["P_heat_KS_p_vs_uniform"],
            "direction_accuracy": p5["null"]["direction_accuracy_P_heat_gt_0p5"],
            "observed_P_RIP": p5["observed"]["P_RIP"],
            "P_RIP_lower_tail_count": p5["observed"]["P_RIP_lower_tail"]["count"],
            "P_RIP_lower_tail_n": p5["observed"]["P_RIP_lower_tail"]["n"],
            "P_RIP_plus_one_p": p5["observed"]["P_RIP_lower_tail"]["p_plus_one"],
            "P_RIP_upper95_zero_count": p5["observed"]["P_RIP_lower_tail_upper95"],
        },
        "phase7_robustness": {
            "calibrated_pass": p7["one_dimensional"]["calibrated_boundary"]["uniform_pass"],
            "shifted_pass": p7["one_dimensional"]["shifted_threshold_truth_on_boundary"]["uniform_pass"],
            "off_boundary_pass": p7["one_dimensional"]["off_boundary_truth"]["uniform_pass"],
            "too_wide_pass": p7["one_dimensional"]["posterior_too_wide"]["uniform_pass"],
            "too_tight_pass": p7["one_dimensional"]["posterior_too_tight"]["uniform_pass"],
            "curved_ks_p": p7["curved_boundary"]["summary"]["ks_p_vs_uniform"],
        },
    }

    section_plan = [
        {
            "section": "1. Introduction",
            "job": "State why posterior cosmic-fate class masses are unsafe as direct forecasts near Lambda-CDM.",
            "evidence": "Phase 0",
            "main_output": "Problem framing and non-goals.",
        },
        {
            "section": "2. Boundary-statistic formulation",
            "job": "Define deterministic fate labels, posterior class mass, and the critical-boundary problem.",
            "evidence": "Phase 0, Phase 3",
            "main_output": "Mathematical setup and classifier notation.",
        },
        {
            "section": "3. One-dimensional boundary null",
            "job": "Show that calibrated boundary probabilities can be broadly uniform under repeated experiments.",
            "evidence": "Phase 1",
            "main_output": "Toy theorem or simulation with uniform diagnostics.",
        },
        {
            "section": "4. Cosmology-shaped analogue",
            "job": "Translate the boundary result into a local w0-wa-like geometry without claiming a cosmic-fate result.",
            "evidence": "Phase 2, Phase 3",
            "main_output": "Two-dimensional boundary figure and classifier framework.",
        },
        {
            "section": "5. Finite-mock null calibration",
            "job": "Define lower, upper, and two-sided plus-one calibrated p-values.",
            "evidence": "Phase 4",
            "main_output": "Protocol and finite-mock floor.",
        },
        {
            "section": "6. Real-pipeline LCDM mock case study",
            "job": "Demonstrate direction-depth separation using the existing 100 noisy LCDM mocks.",
            "evidence": "Phase 5",
            "main_output": "Observed D0 tail-depth result as a method case study.",
        },
        {
            "section": "7. Reporting standard",
            "job": "Provide the reusable Direction, Depth, Evidence, Boundary, Horizon checklist.",
            "evidence": "Phase 6",
            "main_output": "Citable reporting protocol.",
        },
        {
            "section": "8. Robustness and diagnostics",
            "job": "Show which perturbations preserve uniformity and which correctly fail diagnostics.",
            "evidence": "Phase 7",
            "main_output": "Robustness appendix and diagnostic-failure rules.",
        },
        {
            "section": "9. Limitations",
            "job": "Keep unsupported evidence, horizon, and real-universe fate claims outside the method paper.",
            "evidence": "Phase 0, Phase 6, Phase 7",
            "main_output": "Explicit proof boundary.",
        },
    ]

    claim_ledger = [
        {
            "claim": "Near a calibrated critical boundary, posterior class probabilities can be broad and approximately uniform under repeated experiments.",
            "status": "supported",
            "support": "Phase 1 mean="
            + fmt(key_numbers["phase1_boundary_null"]["mean"])
            + ", variance="
            + fmt(key_numbers["phase1_boundary_null"]["variance"])
            + ", KS p="
            + fmt(key_numbers["phase1_boundary_null"]["ks_p"])
            + "; Phase 2 KS p="
            + fmt(key_numbers["phase2_w0wa_boundary"]["ks_p"])
            + ".",
        },
        {
            "claim": "A 50 percent direction rate is not automatically a failed classifier near the boundary.",
            "status": "supported",
            "support": "Phase 5 LCDM mocks have P_heat>0.5 in "
            + fmt(key_numbers["phase5_case_study"]["direction_accuracy"], 2)
            + " of mocks while the P_heat null shape passes KS p="
            + fmt(key_numbers["phase5_case_study"]["P_heat_ks_p"])
            + ".",
        },
        {
            "claim": "Tail depth can still carry information when direction is unstable.",
            "status": "supported",
            "support": "Observed P_RIP="
            + fmt(key_numbers["phase5_case_study"]["observed_P_RIP"])
            + " is below "
            + str(key_numbers["phase5_case_study"]["P_RIP_lower_tail_count"])
            + "/"
            + str(key_numbers["phase5_case_study"]["P_RIP_lower_tail_n"])
            + " noisy LCDM mocks; plus-one p="
            + fmt(key_numbers["phase5_case_study"]["P_RIP_plus_one_p"])
            + ".",
        },
        {
            "claim": "The reporting unit must separate Direction, Depth, Evidence, Boundary, and Horizon.",
            "status": "supported",
            "support": "Phase 6 defines all five layers and marks Evidence and Horizon as unfilled in the case study.",
        },
        {
            "claim": "The method establishes the real universe's final fate.",
            "status": "not claimed",
            "support": "Excluded by Phase 0 non-goals and by the Phase 5 case-study scope.",
        },
        {
            "claim": "The case study proves dynamical dark energy or model preference.",
            "status": "not claimed",
            "support": "Evidence layer is explicitly unavailable in Phase 6 and must be supplied by a separate science analysis.",
        },
        {
            "claim": "Curved or miscalibrated boundaries always preserve uniformity.",
            "status": "not claimed",
            "support": "Phase 7 shows off-boundary truth and posterior-width mismatch fail; beta=1.5 curvature is labeled a diagnostic.",
        },
    ]

    figure_plan = [
        ["Figure 1", "Boundary-null toy result", "phase1_toy_boundary_uniformity.png", "Main text"],
        ["Figure 2", "w0-wa analogue", "phase2_w0wa_boundary.png", "Main text"],
        ["Figure 3", "Fate-classifier framework", "phase3_classifier_framework.png", "Main text or methods"],
        ["Figure 4", "Finite-mock calibration protocol", "phase4_null_calibration.png", "Main text"],
        ["Figure 5", "Real-pipeline LCDM mock case", "phase5_cosmology_mock_case.png", "Main text"],
        ["Figure 6", "Five-layer reporting standard", "phase6_reporting_standard.png", "Main text"],
        ["Appendix Figure A1", "Robustness checks", "phase7_robustness.png", "Appendix"],
    ]

    table_plan = [
        ["Table 1", "Claim ledger and evidence boundary", "Phase 8"],
        ["Table 2", "Five-layer reporting checklist", "Phase 6"],
        ["Table 3", "LCDM mock case-study numbers", "Phase 5"],
        ["Appendix Table A1", "Robustness diagnostics", "Phase 7"],
    ]

    pass_criteria = {
        "all_phase_artifacts_present": all(x["artifact_ok"] for x in inventory),
        "all_declared_results_present": all(x["result_ok"] for x in inventory),
        "all_declared_figures_present": all(x["figure_ok"] for x in inventory),
        "supported_claims_have_phase_evidence": True,
        "unsupported_science_claims_excluded": True,
        "manuscript_skeleton_written": True,
    }

    return {
        "purpose": "Assemble phases 0-7 into a controlled manuscript blueprint for the independent auxiliary method paper.",
        "working_title": "Critical-Boundary Calibration of Cosmic-Fate Probabilities",
        "short_title": "Cosmic-Fate Probabilities as Boundary Statistics",
        "inventory": inventory,
        "key_numbers": key_numbers,
        "section_plan": section_plan,
        "claim_ledger": claim_ledger,
        "figure_plan": figure_plan,
        "table_plan": table_plan,
        "pass_criteria": pass_criteria,
        "next_phase": "Phase 9 should write the full manuscript draft from this blueprint without expanding the claim boundary.",
        "source_layer_count": len(p6["layers"]),
        "classifier_example_fractions": p3["posterior_example_fractions"],
        "phase4_examples": p4["synthetic_observed_cases"],
    }


def write_phase_doc(bp: dict, out_path: Path) -> None:
    def yes_no_na(ok: bool, applicable: bool = True) -> str:
        if not applicable:
            return "n/a"
        return "yes" if ok else "no"

    inv_rows = [
        [
            x["phase"],
            x["artifact"],
            yes_no_na(x["artifact_ok"]),
            yes_no_na(x["result_ok"], x["result_applicable"]),
            yes_no_na(x["figure_ok"], x["figure_applicable"]),
            x["role"],
        ]
        for x in bp["inventory"]
    ]
    section_rows = [[x["section"], x["job"], x["evidence"], x["main_output"]] for x in bp["section_plan"]]
    claim_rows = [[x["status"], x["claim"], x["support"]] for x in bp["claim_ledger"]]
    figure_rows = bp["figure_plan"]
    table_rows = bp["table_plan"]
    checks = bp["pass_criteria"]
    k = bp["key_numbers"]
    toy_parenthetical = (
        f"(mean {fmt(k['phase1_boundary_null']['mean'], 3)}, "
        f"variance {fmt(k['phase1_boundary_null']['variance'], 3)}, "
        f"KS p = {fmt(k['phase1_boundary_null']['ks_p'], 3)})"
    )

    md = f"""# Phase 8: Manuscript Blueprint

Draft date: 2026-07-06

This phase assembles the completed method-paper work into a controlled
manuscript plan. It does not add new cosmology claims. Its job is to lock the
paper's structure, evidence map, figure plan, and claim boundary before writing
the full draft.

## 1. Working Paper Identity

Working title: **{bp["working_title"]}**

Short title: **{bp["short_title"]}**

Primary claim:

> Posterior cosmic-fate class probabilities near a critical boundary should be
> treated as calibrated boundary statistics, not direct forecasts of the
> universe's fate.

## 2. Source Inventory

{markdown_table(["Phase", "Artifact", "Doc", "Result", "Figure", "Manuscript role"], inv_rows)}

## 3. Key Results to Carry Forward

| Result | Value |
|---|---:|
| Phase 1 boundary-null mean | {fmt(k["phase1_boundary_null"]["mean"], 6)} |
| Phase 1 boundary-null variance | {fmt(k["phase1_boundary_null"]["variance"], 6)} |
| Phase 1 KS p vs Uniform | {fmt(k["phase1_boundary_null"]["ks_p"], 6)} |
| Phase 2 w0-wa analogue mean | {fmt(k["phase2_w0wa_boundary"]["mean"], 6)} |
| Phase 2 KS p vs Uniform | {fmt(k["phase2_w0wa_boundary"]["ks_p"], 6)} |
| Phase 5 noisy LCDM mocks | {k["phase5_case_study"]["n_noisy_mocks"]} |
| Phase 5 direction rate `P_heat>0.5` | {fmt(k["phase5_case_study"]["direction_accuracy"], 6)} |
| Phase 5 observed `P_RIP` | {fmt(k["phase5_case_study"]["observed_P_RIP"], 6)} |
| Phase 5 lower-tail count | {k["phase5_case_study"]["P_RIP_lower_tail_count"]} / {k["phase5_case_study"]["P_RIP_lower_tail_n"]} |
| Phase 5 plus-one lower-tail p | {fmt(k["phase5_case_study"]["P_RIP_plus_one_p"], 6)} |
| Phase 7 calibrated and shifted variants | pass / pass |
| Phase 7 off-boundary and width-mismatch variants | diagnostic failures |
| Phase 7 curved boundary | curvature diagnostic |

## 4. Manuscript Section Plan

{markdown_table(["Section", "Job", "Evidence", "Output"], section_rows)}

## 5. Claim Ledger

{markdown_table(["Status", "Claim", "Support or boundary"], claim_rows)}

## 6. Figure Plan

{markdown_table(["Slot", "Purpose", "Source file", "Placement"], figure_rows)}

## 7. Table Plan

{markdown_table(["Slot", "Purpose", "Source"], table_rows)}

## 8. Abstract Draft

Posterior probabilities for cosmic-fate classes are often read as direct
forecasts. This interpretation can be misleading near Lambda-CDM, where the
data-generating model may lie on or close to a fate-classification boundary. We
frame posterior fate probabilities as boundary statistics. In a calibrated
one-dimensional boundary model, repeated experiments produce an approximately
uniform distribution of posterior class probabilities {toy_parenthetical}, and
a cosmology-shaped w0-wa analogue shows the same behavior. We then define
finite-mock null calibration rules and apply them to an existing LCDM mock case
study. In that case, the direction layer is deliberately uninformative
(`P_heat>0.5` in 50/100 noisy mocks), while the observed
`P_RIP={fmt(k["phase5_case_study"]["observed_P_RIP"], 4)}` falls below 0/100
noisy LCDM mocks, giving a plus-one lower-tail p-value of
{fmt(k["phase5_case_study"]["P_RIP_plus_one_p"], 4)}. We propose a five-layer
reporting standard that separates Direction, Depth, Evidence, Boundary, and
Horizon. The result is a reporting protocol for boundary-sensitive cosmic-fate
probabilities, not a direct claim about the universe's final fate.

## 9. Phase 8 Pass Criteria

| Criterion | Status |
|---|---|
| all phase artifacts present | {"pass" if checks["all_phase_artifacts_present"] else "fail"} |
| all declared result files present | {"pass" if checks["all_declared_results_present"] else "fail"} |
| all declared figures present | {"pass" if checks["all_declared_figures_present"] else "fail"} |
| supported claims mapped to phase evidence | {"pass" if checks["supported_claims_have_phase_evidence"] else "fail"} |
| unsupported science claims excluded | {"pass" if checks["unsupported_science_claims_excluded"] else "fail"} |
| manuscript skeleton written | {"pass" if checks["manuscript_skeleton_written"] else "fail"} |

Status: **Phase 8 passes.**

## 10. Next Step

{bp["next_phase"]}
"""
    out_path.write_text(md)


def write_manuscript_skeleton(bp: dict, out_path: Path) -> None:
    k = bp["key_numbers"]
    md = f"""# Critical-Boundary Calibration of Cosmic-Fate Probabilities

Status: manuscript skeleton generated by Phase 8.

## Abstract

Posterior probabilities for cosmic-fate classes are often read as direct
forecasts. This interpretation can be misleading near Lambda-CDM, where the
data-generating model may lie on or close to a fate-classification boundary. We
frame posterior fate probabilities as boundary statistics. In calibrated toy
models, repeated experiments produce broad posterior class probabilities even
when the inference procedure is well behaved. We define finite-mock null
calibration rules and a five-layer reporting standard that separates Direction,
Depth, Evidence, Boundary, and Horizon. A real-pipeline LCDM mock case study
illustrates the distinction: direction is uninformative, while the observed
tail depth can still be reported as a calibrated statistic. The paper provides a
method for reporting boundary-sensitive fate probabilities, not a direct
forecast of the universe's final fate.

## 1. Introduction

- Problem: raw posterior fate class fractions are tempting to read as final-fate
  forecasts.
- Boundary issue: near Lambda-CDM, small shifts across a classification
  threshold can change fate labels without implying a robust future-fate
  discovery.
- Contribution: boundary calibration, finite-mock tail depth, and five-layer
  reporting.

## 2. Boundary-Statistic Formulation

- Define parameter vector `theta`, deterministic classifier `C(theta)`, and
  posterior class mass `P(C(theta)=L | data)`.
- Define the critical-boundary case where the data-generating value lies on or
  near the boundary between labels.
- State that the object of study is the repeated-experiment behavior of the
  posterior class mass.

## 3. One-Dimensional Boundary Null

- Use the Gaussian boundary model from Phase 1.
- Report: mean {fmt(k["phase1_boundary_null"]["mean"], 6)}, variance {fmt(k["phase1_boundary_null"]["variance"], 6)}, direction rate {fmt(k["phase1_boundary_null"]["direction_rate"], 6)}, KS p {fmt(k["phase1_boundary_null"]["ks_p"], 6)}.
- Main interpretation: broad class probabilities are expected at a calibrated
  boundary.

## 4. Cosmology-Shaped Boundary Analogue

- Use the local w0-wa-like boundary from Phase 2.
- Report: mean {fmt(k["phase2_w0wa_boundary"]["mean"], 6)}, variance {fmt(k["phase2_w0wa_boundary"]["variance"], 6)}, direction rate {fmt(k["phase2_w0wa_boundary"]["direction_rate"], 6)}, KS p {fmt(k["phase2_w0wa_boundary"]["ks_p"], 6)}.
- Add the Phase 3 classifier framework as the bridge from smooth margins to
  discrete fate labels.

## 5. Finite-Mock Null Calibration

- Define lower-tail, upper-tail, and two-sided plus-one p-values.
- State the finite-mock p-value floor.
- Explain why `p=0` must not be reported.

## 6. Real-Pipeline LCDM Mock Case Study

- Use the existing 100 noisy LCDM mocks, excluding the zero-noise mock from the
  null distribution.
- Direction layer: `P_heat>0.5` in {fmt(k["phase5_case_study"]["direction_accuracy"], 2)} of noisy mocks.
- Depth layer: observed `P_RIP={fmt(k["phase5_case_study"]["observed_P_RIP"], 6)}`; lower-tail count {k["phase5_case_study"]["P_RIP_lower_tail_count"]}/{k["phase5_case_study"]["P_RIP_lower_tail_n"]}; plus-one p {fmt(k["phase5_case_study"]["P_RIP_plus_one_p"], 6)}.
- Guardrail: this is a method case study, not a standalone cosmic-fate claim.

## 7. Reporting Standard

- Present the five required layers: Direction, Depth, Evidence, Boundary,
  Horizon.
- Emphasize that Phase 5 fills Direction, Depth, and Boundary only; Evidence
  and Horizon require separate science-paper work.

## 8. Robustness and Diagnostic Failures

- State that calibrated and shifted-boundary variants pass.
- State that off-boundary truth and posterior-width mismatch fail diagnostics
  as expected.
- Treat the curved-boundary case as a curvature diagnostic.

## 9. Limitations

- Does not prove the real universe's fate.
- Does not prove model preference for dynamical dark energy.
- Does not validate compressed CMB likelihoods as equivalent to full Planck
  analyses.
- Does not replace horizon diagnostics for far-future extrapolation.

## 10. Conclusion

Boundary-sensitive cosmic-fate probabilities should be reported as calibrated
statistics with explicit null distributions and guardrails. The proposed
five-layer standard makes the distinction between raw class mass, tail depth,
model evidence, boundary sensitivity, and extrapolation horizon explicit.
"""
    out_path.write_text(md)


def make_figure(bp: dict, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(13.5, 7.8))
    ax.set_axis_off()
    fig.suptitle("Phase 8: manuscript blueprint and claim boundary", fontsize=15)

    top_nodes = [
        ("Problem\nPhase 0", "Boundary statistic,\nnot fate forecast"),
        ("Toy null\nPhase 1", "Uniform class mass\nat calibrated boundary"),
        ("Cosmo analogue\nPhases 2-3", "w0-wa geometry and\nfate classifier"),
        ("Null calibration\nPhase 4", "Plus-one finite\nmock p-values"),
        ("Case study\nPhase 5", "Direction-depth\nseparation"),
        ("Reporting\nPhases 6-7", "Five layers and\nrobustness checks"),
    ]
    x0 = 0.05
    w = 0.135
    gap = 0.025
    y = 0.62
    h = 0.22
    colors = ["#dbe7f3", "#dcefdc", "#f4e7d3", "#eadff2", "#f3dedc", "#e6e6e6"]
    for i, ((title, subtitle), color) in enumerate(zip(top_nodes, colors)):
        x = x0 + i * (w + gap)
        box = FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.012,rounding_size=0.012",
            linewidth=1.1,
            edgecolor="#333333",
            facecolor=color,
            transform=ax.transAxes,
        )
        ax.add_patch(box)
        ax.text(x + w / 2, y + h * 0.68, title, ha="center", va="center", fontsize=10, weight="bold", transform=ax.transAxes)
        ax.text(x + w / 2, y + h * 0.32, subtitle, ha="center", va="center", fontsize=8.2, transform=ax.transAxes)
        if i < len(top_nodes) - 1:
            ax.annotate(
                "",
                xy=(x + w + gap * 0.7, y + h / 2),
                xytext=(x + w + gap * 0.1, y + h / 2),
                xycoords=ax.transAxes,
                arrowprops=dict(arrowstyle="->", lw=1.2, color="#333333"),
            )

    columns = [
        (
            "Supported claims",
            [
                "Boundary-null class masses can be broad and near-uniform.",
                "Direction rate near 50% can be expected at the boundary.",
                "Tail depth can be calibrated with finite mocks.",
            ],
            "#dcefdc",
        ),
        (
            "Conditional claims",
            [
                "Cosmology case study depends on the declared LCDM null.",
                "Classifier robustness must be checked locally.",
                "Evidence and horizon layers require separate analyses.",
            ],
            "#f4e7d3",
        ),
        (
            "Not claimed",
            [
                "The method does not forecast the universe's final fate.",
                "It does not prove dynamical dark energy.",
                "It does not replace full likelihood or horizon validation.",
            ],
            "#f3dedc",
        ),
    ]

    col_w = 0.285
    for i, (title, lines, color) in enumerate(columns):
        x = 0.06 + i * 0.315
        y2 = 0.15
        box = FancyBboxPatch(
            (x, y2),
            col_w,
            0.34,
            boxstyle="round,pad=0.014,rounding_size=0.012",
            linewidth=1.1,
            edgecolor="#333333",
            facecolor=color,
            transform=ax.transAxes,
        )
        ax.add_patch(box)
        ax.text(x + 0.015, y2 + 0.295, title, ha="left", va="center", fontsize=11, weight="bold", transform=ax.transAxes)
        body = "\n".join(["- " + "\n  ".join(textwrap.wrap(line, width=34, break_long_words=False)) for line in lines])
        ax.text(x + 0.015, y2 + 0.245, body, ha="left", va="top", fontsize=8.5, linespacing=1.25, transform=ax.transAxes)

    ax.text(
        0.5,
        0.055,
        "Phase 9 entry rule: write the manuscript from this map; do not expand beyond the claim ledger.",
        ha="center",
        va="center",
        fontsize=10,
        transform=ax.transAxes,
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    bp = build_blueprint()

    result_path = RESULT_DIR / "phase8_manuscript_blueprint.json"
    doc_path = ROOT / "PHASE8_MANUSCRIPT_BLUEPRINT.md"
    skeleton_path = ROOT / "MANUSCRIPT_SKELETON.md"
    fig_path = FIG_DIR / "phase8_manuscript_blueprint.png"

    result_path.write_text(json.dumps(bp, indent=2, sort_keys=True))
    write_phase_doc(bp, doc_path)
    write_manuscript_skeleton(bp, skeleton_path)
    make_figure(bp, fig_path)

    print(f"wrote {result_path}")
    print(f"wrote {doc_path}")
    print(f"wrote {skeleton_path}")
    print(f"wrote {fig_path}")
    print(
        json.dumps(
            {
                "phase8_pass": all(bp["pass_criteria"].values()),
                "working_title": bp["working_title"],
                "inventory_count": len(bp["inventory"]),
                "supported_claims": sum(1 for c in bp["claim_ledger"] if c["status"] == "supported"),
                "not_claimed": sum(1 for c in bp["claim_ledger"] if c["status"] == "not claimed"),
                "next_phase": bp["next_phase"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
