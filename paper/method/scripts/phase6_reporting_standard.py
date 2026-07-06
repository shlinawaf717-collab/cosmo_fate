#!/usr/bin/env python3
"""Phase 6 reporting standard.

Build a reusable checklist, a markdown reporting template, and a figure for the
method paper's reporting standard. The script reads the Phase 5 case-study
summary only to populate the example column.
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
FIG_DIR = ROOT / "figures"
RESULT_DIR = ROOT / "results"
PHASE5_JSON = RESULT_DIR / "phase5_cosmology_mock_case.json"


LAYERS = [
    {
        "layer": "Direction",
        "question": "Which label has more posterior mass?",
        "required": [
            "raw P(label | data)",
            "direction threshold, usually 0.5",
            "same quantity under null mocks",
        ],
        "failure_mode": "Treating P > 0.5 as a discovery near a boundary.",
    },
    {
        "layer": "Depth",
        "question": "How unusual is the raw probability under the null?",
        "required": [
            "predeclared null model",
            "mock count and finite-mock floor",
            "lower-tail, upper-tail, and two-sided calibrated p-values",
        ],
        "failure_mode": "Reporting a raw tail probability without null calibration.",
    },
    {
        "layer": "Evidence",
        "question": "Does the enlarged model deserve preference?",
        "required": [
            "likelihood-ratio or delta chi2 where appropriate",
            "AIC/BIC or Bayes factor where available",
            "clear separation from fate-class probability",
        ],
        "failure_mode": "Confusing a class probability with evidence for the model.",
    },
    {
        "layer": "Boundary",
        "question": "Is the label sensitive to thresholds or classifier defects?",
        "required": [
            "boundary-flip fraction or threshold sensitivity",
            "OTHER fraction and audit rule",
            "known classifier limitations",
        ],
        "failure_mode": "Hiding that posterior mass lies near a label boundary.",
    },
    {
        "layer": "Horizon",
        "question": "Is the fate decision inside the data-constrained region?",
        "required": [
            "future scale used by the classifier",
            "constraint horizon or equivalent diagnostic",
            "statement when the horizon diagnostic is unavailable",
        ],
        "failure_mode": "Interpreting unconstrained far-future extrapolation as data.",
    },
]


def case_example(phase5: dict) -> dict[str, str]:
    null = phase5["null"]
    obs = phase5["observed"]
    return {
        "Direction": (
            f"Observed P_heat={obs['P_heat']:.5f}; LCDM null has "
            f"P_heat>0.5 in {int(null['direction_accuracy_P_heat_gt_0p5'] * null['n_noisy_mocks'])}/"
            f"{null['n_noisy_mocks']} mocks."
        ),
        "Depth": (
            f"Observed P_RIP={obs['P_RIP']:.5f}; "
            f"{obs['n_null_P_RIP_below_or_equal_observed']}/{obs['P_RIP_lower_tail']['n']} "
            f"null mocks are lower; plus-one p={obs['P_RIP_lower_tail']['p_plus_one']:.5f}, "
            f"95% CP upper={obs['P_RIP_lower_tail_upper95']:.5f}."
        ),
        "Evidence": (
            "Not evaluated by the Phase 5 case-study figure; a science paper must "
            "add likelihood-ratio, AIC/BIC, or Bayes-factor evidence separately."
        ),
        "Boundary": (
            f"max OTHER={null['OTHER_max']:.5f}; max boundary fraction={null['boundary_max']:.5f}; "
            f"mock000 P_heat={null['mock000']['P_heat']:.5f}."
        ),
        "Horizon": (
            "Not evaluated by the Phase 5 case-study figure; a science paper must "
            "report constraint horizon or explicitly mark it unavailable."
        ),
    }


def make_markdown_template(path: Path) -> None:
    lines = [
        "# Fate-Probability Reporting Checklist",
        "",
        "Use this template whenever reporting a posterior fate probability near a",
        "critical boundary.",
        "",
        "## Metadata",
        "",
        "- Dataset / mock set:",
        "- Model / parameterization:",
        "- Classifier version:",
        "- Null model:",
        "- Number of null mocks:",
        "- Finite-mock p-value floor:",
        "",
        "## Required Layers",
        "",
    ]
    for item in LAYERS:
        lines.extend(
            [
                f"### {item['layer']}",
                "",
                f"Question: {item['question']}",
                "",
                "Required fields:",
                "",
            ]
        )
        for field in item["required"]:
            lines.append(f"- [ ] {field}")
        lines.extend(["", f"Failure mode to avoid: {item['failure_mode']}", ""])
    lines.extend(
        [
            "## Minimum Claim Language",
            "",
            "Raw class probability:",
            "",
            "> The posterior mass in label L is ...",
            "",
            "Calibrated boundary statistic:",
            "",
            "> Under the predeclared null, the observed class probability lies in the ... tail with finite-mock-calibrated p = ...",
            "",
            "Guardrail:",
            "",
            "> This is not, by itself, a direct forecast of the universe's fate.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def make_figure(phase5: dict, out_path: Path) -> None:
    examples = case_example(phase5)
    fig, ax = plt.subplots(figsize=(15.5, 10.2), constrained_layout=True)
    ax.axis("off")
    ax.set_title("Phase 6: reporting standard for calibrated fate probabilities", fontsize=15, pad=16)

    col_x = [0.025, 0.17, 0.42, 0.70]
    headers = ["Layer", "Question", "Required report", "Phase 5 case-study fill"]
    for x, h in zip(col_x, headers):
        ax.text(x, 0.94, h, transform=ax.transAxes, fontsize=10, fontweight="bold", va="top")

    y = 0.86
    row_h = 0.158
    colors = ["#eef4fb", "#f7f7f7"]
    for i, item in enumerate(LAYERS):
        face = colors[i % 2]
        ax.add_patch(
            plt.Rectangle((0.01, y - row_h + 0.012), 0.98, row_h - 0.014, transform=ax.transAxes,
                          facecolor=face, edgecolor="#dddddd", linewidth=0.8)
        )
        ax.text(col_x[0], y, item["layer"], transform=ax.transAxes, fontsize=10, fontweight="bold", va="top")
        question = textwrap.fill(item["question"], width=35)
        req = "\n".join(textwrap.fill(f"- {field}", width=42, subsequent_indent="  ") for field in item["required"])
        example = textwrap.fill(examples[item["layer"]], width=55)
        ax.text(col_x[1], y, question, transform=ax.transAxes, fontsize=8.8, va="top")
        ax.text(col_x[2], y, req, transform=ax.transAxes, fontsize=8.1, va="top")
        ax.text(col_x[3], y, example, transform=ax.transAxes, fontsize=8.1, va="top")
        y -= row_h

    ax.text(
        0.02,
        0.035,
        "Rule: do not report a fate probability as a direct forecast until direction, depth, evidence, boundary, and horizon layers are separated.",
        transform=ax.transAxes,
        fontsize=10,
        fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.45", facecolor="#fff6df", edgecolor="#9a7a2f"),
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=220)
    plt.close(fig)


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_DIR.mkdir(parents=True, exist_ok=True)

    phase5 = json.loads(PHASE5_JSON.read_text(encoding="utf-8"))
    checklist = {
        "purpose": "Standard reporting checklist for posterior fate probabilities near critical boundaries.",
        "layers": LAYERS,
        "phase5_case_study_fill": case_example(phase5),
        "minimum_required_statement": (
            "Report raw class mass, null-calibrated tail depth, model evidence, "
            "boundary sensitivity, and horizon status as separate claims."
        ),
    }

    json_path = RESULT_DIR / "phase6_reporting_standard.json"
    template_path = ROOT / "REPORTING_CHECKLIST_TEMPLATE.md"
    fig_path = FIG_DIR / "phase6_reporting_standard.png"

    json_path.write_text(json.dumps(checklist, indent=2), encoding="utf-8")
    make_markdown_template(template_path)
    make_figure(phase5, fig_path)

    print(f"wrote {json_path}")
    print(f"wrote {template_path}")
    print(f"wrote {fig_path}")


if __name__ == "__main__":
    main()
