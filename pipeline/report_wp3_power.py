"""Create paper-facing WP3 power tables and a complete six-point curve."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
WP3_ROOT = ROOT / "runs" / "prd_extension" / "wp3_power"
AUDIT = WP3_ROOT / "completion_audit.json"
ORDER = ("wam060", "wam030", "wam015", "wap015", "wap030", "wap060")


def _interval_text(interval: list[float]) -> str:
    return f"[{interval[0]:.3f}, {interval[1]:.3f}]"


def load_truth_profiles(root: Path = WP3_ROOT) -> dict[str, dict]:
    profiles = {}
    for truth_id in ORDER:
        path = root / "truths" / truth_id / "truth.json"
        truth = json.loads(path.read_text(encoding="utf-8"))
        profiles[truth_id] = {
            "profile_chi2": float(truth["fit"]["chi2"]),
            "source": str(path.relative_to(ROOT)),
        }
    reference = min(row["profile_chi2"] for row in profiles.values())
    for row in profiles.values():
        row["delta_chi2_from_best_registered_truth"] = (
            row["profile_chi2"] - reference
        )
    return profiles


def build_report(audit: dict, truth_profiles: dict[str, dict] | None = None) -> dict:
    if audit.get("status") != "PASS":
        raise ValueError("WP3 completion audit has not passed")
    if truth_profiles is None:
        truth_profiles = load_truth_profiles()
    registered = audit["registered_power_endpoints"]
    points = registered["truth_points"]
    rows = []
    for truth_id in ORDER:
        point = points[truth_id]
        rows.append(
            {
                "truth_id": truth_id,
                "wa": point["wa"],
                "profile_chi2": truth_profiles[truth_id]["profile_chi2"],
                "delta_chi2_from_best_registered_truth": truth_profiles[
                    truth_id
                ]["delta_chi2_from_best_registered_truth"],
                "truth_fit_source": truth_profiles[truth_id]["source"],
                "correct_direction": point["correct_direction"],
                "direction_power": point["direction_power"]["rate"],
                "direction_power_exact95": point["direction_power"][
                    "exact_binomial_95_interval"
                ],
                "depth_power": point["one_sided_depth_power"]["rate"],
                "depth_power_exact95": point["one_sided_depth_power"][
                    "exact_binomial_95_interval"
                ],
                "false_sign_fraction": point["false_sign_fraction"]["rate"],
                "false_sign_exact95": point["false_sign_fraction"][
                    "exact_binomial_95_interval"
                ],
                "correct_mass_median": point["correct_mass_distribution"]["median"],
                "correct_mass_central68": point["correct_mass_distribution"][
                    "central_68_interval"
                ],
                "asimov_correct_mass": point["asimov_correct_mass"],
            }
        )
    return {
        "schema_version": "wp3-power-report-v2",
        "source_audit": str(AUDIT.relative_to(ROOT)),
        "completion_status": audit["status"],
        "outer_direction_power_threshold": registered[
            "outer_direction_power_threshold"
        ],
        "outer_points_pass": registered["outer_points_pass"],
        "positive_claim_scope": registered["positive_claim_scope"],
        "monotonicity_status": registered["monotonicity_diagnostic"]["status"],
        "monotonicity_evidential_role": registered[
            "monotonicity_diagnostic"
        ]["evidential_role"],
        "rows": rows,
        "interpretation_guardrail": (
            "Power is truth-specific. The six declared alternatives have "
            "different profile chi-square penalties against the observed D0 "
            "data and are not a symmetric sequence of equally supported "
            "effect sizes. WP3 establishes strong direction power under the "
            "two registered outer-point alternatives; it does not establish "
            "that the observed universe occupies any one off-boundary truth."
        ),
    }


def write_csv(report: dict, path: Path) -> None:
    fields = (
        "truth_id",
        "wa",
        "profile_chi2",
        "delta_chi2_from_best_registered_truth",
        "correct_direction",
        "direction_power",
        "direction_low95",
        "direction_high95",
        "depth_power",
        "depth_low95",
        "depth_high95",
        "false_sign_fraction",
        "false_sign_low95",
        "false_sign_high95",
        "correct_mass_median",
        "correct_mass_low68",
        "correct_mass_high68",
        "asimov_correct_mass",
    )
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in report["rows"]:
            writer.writerow(
                {
                    "truth_id": row["truth_id"],
                    "wa": row["wa"],
                    "profile_chi2": row["profile_chi2"],
                    "delta_chi2_from_best_registered_truth": row[
                        "delta_chi2_from_best_registered_truth"
                    ],
                    "correct_direction": row["correct_direction"],
                    "direction_power": row["direction_power"],
                    "direction_low95": row["direction_power_exact95"][0],
                    "direction_high95": row["direction_power_exact95"][1],
                    "depth_power": row["depth_power"],
                    "depth_low95": row["depth_power_exact95"][0],
                    "depth_high95": row["depth_power_exact95"][1],
                    "false_sign_fraction": row["false_sign_fraction"],
                    "false_sign_low95": row["false_sign_exact95"][0],
                    "false_sign_high95": row["false_sign_exact95"][1],
                    "correct_mass_median": row["correct_mass_median"],
                    "correct_mass_low68": row["correct_mass_central68"][0],
                    "correct_mass_high68": row["correct_mass_central68"][1],
                    "asimov_correct_mass": row["asimov_correct_mass"],
                }
            )


def write_markdown(report: dict, path: Path) -> None:
    lines = [
        "# WP3 off-boundary power report",
        "",
        "| Truth | wa | profile chi2 | delta chi2 | Correct side | Direction power (exact 95%) | Depth power (exact 95%) | False sign (exact 95%) | Correct mass median [central 68%] |",
        "|---|---:|---:|---:|---|---:|---:|---:|---:|",
    ]
    for row in report["rows"]:
        lines.append(
            "| {truth_id} | {wa:+.2f} | {chi2:.2f} | {delta_chi2:.2f} "
            "| {side} | {direction:.2f} {direction_ci} "
            "| {depth:.2f} {depth_ci} | {false:.2f} {false_ci} | "
            "{median:.3f} [{low68:.3f}, {high68:.3f}] |".format(
                truth_id=row["truth_id"],
                wa=row["wa"],
                chi2=row["profile_chi2"],
                delta_chi2=row["delta_chi2_from_best_registered_truth"],
                side=row["correct_direction"],
                direction=row["direction_power"],
                direction_ci=_interval_text(row["direction_power_exact95"]),
                depth=row["depth_power"],
                depth_ci=_interval_text(row["depth_power_exact95"]),
                false=row["false_sign_fraction"],
                false_ci=_interval_text(row["false_sign_exact95"]),
                median=row["correct_mass_median"],
                low68=row["correct_mass_central68"][0],
                high68=row["correct_mass_central68"][1],
            )
        )
    status = "PASS" if report["outer_points_pass"] else "FAIL"
    lines.extend(
        [
            "",
            f"- Outer-point direction-power gate (`>=0.80`): **{status}**.",
            f"- Positive claim: {report['positive_claim_scope']}.",
            f"- Coarse monotonicity diagnostic: "
            f"**{report['monotonicity_status']}**; "
            f"{report['monotonicity_evidential_role']}.",
            "",
            report["interpretation_guardrail"],
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_figure(report: dict, path: Path) -> None:
    rows = report["rows"]
    x = np.asarray([row["wa"] for row in rows])
    fig, axes = plt.subplots(1, 2, figsize=(10.8, 4.3), constrained_layout=True)

    for ax, key, ci_key, label, color in (
        (
            axes[0],
            "direction_power",
            "direction_power_exact95",
            "Direction power",
            "#315f9d",
        ),
        (
            axes[1],
            "depth_power",
            "depth_power_exact95",
            "One-sided depth power",
            "#a64b3c",
        ),
    ):
        y = np.asarray([row[key] for row in rows])
        intervals = np.asarray([row[ci_key] for row in rows])
        yerr = np.vstack((y - intervals[:, 0], intervals[:, 1] - y))
        ax.errorbar(
            x,
            y,
            yerr=yerr,
            marker="o",
            markersize=5,
            linewidth=1.7,
            capsize=3,
            color=color,
        )
        for x_value, y_value, row in zip(x, y, rows):
            ax.annotate(
                rf"$\Delta\chi^2={row['delta_chi2_from_best_registered_truth']:.1f}$",
                (x_value, y_value),
                xytext=(0, -15 if y_value > 0.94 else 8),
                textcoords="offset points",
                ha="center",
                fontsize=6.5,
                color="#444444",
            )
        ax.axvline(0, color="#777777", linewidth=0.9, linestyle=":")
        ax.set_xlabel(r"Truth $w_a$")
        ax.set_ylabel(label)
        ax.set_ylim(-0.03, 1.05)
        ax.set_xticks(x)
        ax.grid(axis="y", alpha=0.2)
    axes[0].axhline(
        report["outer_direction_power_threshold"],
        color="#333333",
        linestyle="--",
        linewidth=1,
        label="Registered outer-point threshold",
    )
    axes[0].legend(frameon=False, fontsize=8, loc="lower right")
    fig.suptitle(
        "WP3 truth-specific power; registered alternatives are not equally "
        "supported by observed D0"
    )
    fig.savefig(path, dpi=220)
    plt.close(fig)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", type=Path, default=AUDIT)
    parser.add_argument("--output-dir", type=Path, default=WP3_ROOT)
    args = parser.parse_args(argv)
    audit = json.loads(args.audit.read_text(encoding="utf-8"))
    report = build_report(audit)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "power_report.json"
    csv_path = args.output_dir / "power_curve.csv"
    markdown_path = args.output_dir / "POWER_REPORT.md"
    figure_path = args.output_dir / "power_curve.png"
    json_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_csv(report, csv_path)
    write_markdown(report, markdown_path)
    write_figure(report, figure_path)
    print(
        json.dumps(
            {
                "json": str(json_path),
                "csv": str(csv_path),
                "markdown": str(markdown_path),
                "figure": str(figure_path),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
