#!/usr/bin/env python3
"""Build the frozen WP4 F1 full-CMB + Pantheon+SH0ES configuration."""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml

from pipeline.wp4_preflight import ROOT


F0_CONFIG = ROOT / "pipeline/wp4_f0.yaml"
DEFAULT_OUTPUT = ROOT / "pipeline/wp4_f1.yaml"


class F1ConfigError(RuntimeError):
    """Raised when the F0 template cannot be transformed unambiguously."""


def build_config() -> dict:
    config = yaml.safe_load(F0_CONFIG.read_text(encoding="utf-8"))
    likelihood = config["likelihood"]
    if "sn.pantheonplus" not in likelihood:
        raise F1ConfigError("F0 Pantheon+ likelihood is missing")
    if "sn.pantheonplusshoes" in likelihood:
        raise F1ConfigError("F0 template unexpectedly already contains SH0ES")
    transformed_likelihood = {}
    for name, settings in likelihood.items():
        if name == "sn.pantheonplus":
            transformed_likelihood["sn.pantheonplusshoes"] = {
                "use_abs_mag": True,
                "stop_at_error": False,
            }
        else:
            transformed_likelihood[name] = settings
    config["likelihood"] = transformed_likelihood

    # F1 is the like-for-like full-likelihood replacement for v1.x D0, whose
    # frozen P1 prior requires early matter domination in native CPL coordinates.
    config["prior"] = {
        "matter_dom": "lambda w, wa: 0 if (w + wa) < 0 else -1e30"
    }
    params = config["params"]
    if "Mb" in params:
        raise F1ConfigError("F0 template unexpectedly already contains Mb")
    transformed_params = {}
    for name, settings in params.items():
        transformed_params[name] = settings
        if name == "wa":
            transformed_params["Mb"] = {
                "prior": {"min": -20.0, "max": -18.0},
                "ref": {"dist": "norm", "loc": -19.25, "scale": 0.03},
                "proposal": 0.02,
                "latex": "M_B",
            }
    config["params"] = transformed_params

    mcmc = config["sampler"]["mcmc"]
    mcmc["covmat"] = (
        "{YAML_ROOT}/../runs/prd_extension/wp4_full_cmb/f1_proposal.covmat"
    )
    # The authoritative prospective external rule stops F1. These strict
    # internal values prevent --no-mpi's different split-chain rule from
    # terminating production first.
    mcmc["Rminus1_stop"] = 1e-6
    mcmc["Rminus1_cl_stop"] = 1e-6
    blocking = mcmc["blocking"]
    if "Mb" not in blocking[-1][1]:
        blocking[-1][1].append("Mb")
    mcmc["seed"] = 4500
    config["output"] = (
        "{YAML_ROOT}/../runs/prd_extension/wp4_full_cmb/f1_smoke/chain"
    )
    return config


def validate_config(config: dict) -> None:
    likelihood = config["likelihood"]
    if "sn.pantheonplusshoes" not in likelihood or "sn.pantheonplus" in likelihood:
        raise F1ConfigError("F1 must replace Pantheon+ with Pantheon+SH0ES")
    if likelihood["sn.pantheonplusshoes"].get("use_abs_mag") is not True:
        raise F1ConfigError("F1 SH0ES likelihood must sample absolute magnitude")
    if config.get("prior", {}).get("matter_dom") != (
        "lambda w, wa: 0 if (w + wa) < 0 else -1e30"
    ):
        raise F1ConfigError("F1 does not preserve the frozen P1 prior")
    if "Mb" not in config["params"]:
        raise F1ConfigError("F1 absolute magnitude parameter is missing")
    if "f1_proposal.covmat" not in config["sampler"]["mcmc"]["covmat"]:
        raise F1ConfigError("F1 proposal covariance is not selected")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    config = build_config()
    validate_config(config)
    args.output.write_text(
        yaml.safe_dump(config, sort_keys=False, width=100), encoding="utf-8"
    )
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
