#!/usr/bin/env python3
"""Fulfil the registered F_prior, F_param, and F_data log-span metrics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSON = ROOT / "runs/phase3/fragility_metrics.json"
DEFAULT_MD = ROOT / "paper/FRAGILITY_METRICS.md"


def portable_float(value):
    """Round platform-level arithmetic noise while retaining 12 significant digits."""
    return float(f"{float(value):.12g}")


def load(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def fate_values(rel: str) -> tuple[float, float]:
    row = load(rel)
    fate = row.get("P_fate_weighted", row.get("P_fate_nested", row))
    rip = float(fate["RIP"]["P"] if isinstance(fate["RIP"], dict) else fate["RIP"])
    if "P_heat" in row:
        heat = float(row["P_heat"])
    elif "P_heat_death_compatible" in row:
        heat = float(row["P_heat_death_compatible"])
    else:
        def scalar(label):
            value = fate[label]
            return float(value["P"] if isinstance(value, dict) else value)
        heat = scalar("DS") + scalar("DECAY")
    return rip, heat


def log_span(entries: list[dict], quantity: str) -> dict:
    values = np.asarray([row[quantity] for row in entries], dtype=float)
    zero_rows = [row for row in entries if row[quantity] == 0.0]
    positive = values[values > 0.0]
    base = {
        "quantity": quantity,
        "min": float(values.min()),
        "max": float(values.max()),
        "zero_members": [row["name"] for row in zero_rows],
    }
    if zero_rows:
        kinds = {row.get(f"{quantity}_zero_kind") for row in zero_rows}
        if kinds <= {"structural_prior", "exact_construction"}:
            return {**base, "log10_span_dex": None, "display": "infinite",
                    "status": "structurally_unbounded_by_exact_zero"}
        lower = None if len(positive) < 2 else portable_float(
            np.log10(positive.max()) - np.log10(positive.min())
        )
        return {**base, "log10_span_dex": None, "positive_only_lower_bound_dex": lower,
                "display": "not point-identifiable",
                "status": "finite_nested_sampling_zero_requires_limit_or_more_runs"}
    span = portable_float(np.log10(values.max()) - np.log10(values.min()))
    return {**base, "log10_span_dex": span, "display": f"{span:.3f} dex", "status": "finite"}


def make_entries(specs: list[tuple[str, str, str | None]]) -> list[dict]:
    out = []
    for name, path, zero_kind in specs:
        rip, heat = fate_values(path)
        out.append({
            "name": name, "source": path, "P_RIP": rip, "P_heat": heat,
            "P_RIP_zero_kind": zero_kind if rip == 0.0 else None,
            "P_heat_zero_kind": zero_kind if heat == 0.0 else None,
        })
    return out


def compute() -> dict:
    prior = make_entries([
        ("P1", "runs/phase2/fate/d0_cpl_p1.json", None),
        ("P2", "runs/phase3/fprior/fate_p2.json", "structural_prior"),
        ("P3", "runs/phase3/fprior/fate_p3.json", "structural_prior"),
    ])
    fitted = make_entries([
        ("CPL", "runs/phase3/fparam/fate_cpl.json", None),
        ("BA", "runs/phase3/fparam/fate_ba_a005.json", None),
        ("JBP", "runs/phase3/fparam/fate_jbp.json", None),
        ("BIN4", "runs/phase3/fparam/fate_bin4_a005.json", None),
    ])
    param = fitted + make_entries([
        ("GP construction", "runs/phase3/fparam/fate_gp.json", "exact_construction"),
    ])
    data = make_entries([
        ("D0", "runs/phase2/nested_d0.json", "finite_nested_sampling"),
        ("D1", "runs/phase3/fdata/nested_d1.json", "finite_nested_sampling"),
        ("D2", "runs/phase3/fdata/nested_d2.json", "finite_nested_sampling"),
        ("D3", "runs/phase3/fdata/nested_d3.json", "finite_nested_sampling"),
        ("D4", "runs/phase3/fdata/nested_d4.json", "finite_nested_sampling"),
    ])

    def axis(entries):
        return {
            "members": entries,
            "P_RIP": log_span(entries, "P_RIP"),
            "P_heat": log_span(entries, "P_heat"),
        }

    return {
        "schema_version": "fragility-metrics-v1-a005",
        "definition": "max(log10 P) - min(log10 P) across the registered axis",
        "F_prior": axis(prior),
        "F_param": axis(param),
        "F_param_fitted_four_diagnostic": axis(fitted),
        "F_data": axis(data),
        "interpretation_rules": [
            "An exact zero imposed by a prior or deterministic construction makes the registered log span infinite.",
            "A zero observed in a finite nested run is not treated as a mathematical zero; the point span is withheld pending an upper limit or additional resolution.",
            "F_param changes grammar, native dimension, future rule, and registered coordinate prior as one coupled audit package.",
        ],
    }


def render_markdown(result: dict) -> str:
    lines = [
        "# Registered fragility metrics (A-005 semantics)", "",
        "The registered metric is `max(log10 P) - min(log10 P)` along each axis.", "",
        "| Axis | Quantity | Result | Status | Range |", "|---|---|---:|---|---|",
    ]
    for key in ("F_prior", "F_param", "F_param_fitted_four_diagnostic", "F_data"):
        for quantity in ("P_RIP", "P_heat"):
            row = result[key][quantity]
            lines.append(
                f"| {key} | {quantity} | {row['display']} | {row['status']} | "
                f"{row['min']:.8g}--{row['max']:.8g} |"
            )
    lines += ["", "Exact prior/construction zeros and finite-sampling zeros are not conflated.", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()
    result = compute()
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    args.markdown.write_text(render_markdown(result), encoding="utf-8")
    print(f"wrote {args.output}")
    print(f"wrote {args.markdown}")


if __name__ == "__main__":
    main()
