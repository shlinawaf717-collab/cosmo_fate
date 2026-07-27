#!/usr/bin/env python3
"""Create the portable WP4 F0 config from the archived official DESI config.

Only public-package/path normalization is performed.  The registered data
combination, theory settings, cosmological priors, nuisance priors, and
likelihood options are inherited from the archived official YAML.
"""

from __future__ import annotations

import argparse
import copy
from pathlib import Path

import yaml

from pipeline.wp4_preflight import (
    EXPECTED_OFFICIAL_LIKELIHOODS,
    OFFICIAL_ROOT,
    ROOT,
)


DEFAULT_OUTPUT = ROOT / "pipeline" / "wp4_f0.yaml"
OFFICIAL_CONFIG = OFFICIAL_ROOT / "chain.updated.yaml"

OFFICIAL_BAO = EXPECTED_OFFICIAL_LIKELIHOODS[0]
PUBLIC_BAO = "bao.desi_dr2.desi_bao_all"
OFFICIAL_ACT = EXPECTED_OFFICIAL_LIKELIHOODS[-1]
PUBLIC_ACT = "act_dr6_lenslike.ACTDR6LensLike"


class WP4ConfigError(RuntimeError):
    """Raised when the archived config no longer matches the frozen protocol."""


def _keep(mapping: dict, names: tuple[str, ...]) -> dict:
    return {name: copy.deepcopy(mapping[name]) for name in names if name in mapping}


def prepare_config(source: Path = OFFICIAL_CONFIG) -> dict:
    official = yaml.safe_load(source.read_text(encoding="utf-8"))
    likelihoods = tuple(official.get("likelihood", {}))
    if likelihoods != EXPECTED_OFFICIAL_LIKELIHOODS:
        raise WP4ConfigError(
            "official likelihood identity/order differs from the frozen WP4 protocol"
        )

    config = {
        "packages_path": "{YAML_ROOT}/../data/cobaya_packages",
        "theory": {
            "camb": _keep(
                official["theory"]["camb"],
                ("extra_args", "stop_at_error", "ignore_obsolete"),
            )
        },
        "likelihood": {},
        "params": copy.deepcopy(official["params"]),
        "sampler": {"mcmc": copy.deepcopy(official["sampler"]["mcmc"])},
        "output": (
            "{YAML_ROOT}/../runs/prd_extension/wp4_full_cmb/f0_smoke/chain"
        ),
    }
    config["theory"]["camb"]["path"] = "global"

    official_likes = official["likelihood"]
    config["likelihood"][PUBLIC_BAO] = {}
    config["likelihood"]["sn.pantheonplus"] = _keep(
        official_likes["sn.pantheonplus"],
        ("use_abs_mag", "stop_at_error"),
    )
    for name in (
        "planck_2018_lowl.TT_clik",
        "planck_2018_lowl.EE_clik",
    ):
        config["likelihood"][name] = _keep(
            official_likes[name],
            ("clik_file", "product_id", "stop_at_error"),
        )
    config["likelihood"]["planck_NPIPE_highl_CamSpec.TTTEEE"] = _keep(
        official_likes["planck_NPIPE_highl_CamSpec.TTTEEE"],
        ("dataset_file", "dataset_params", "stop_at_error"),
    )
    config["likelihood"][PUBLIC_ACT] = _keep(
        official_likes[OFFICIAL_ACT],
        (
            "lmax",
            "mock",
            "nsims_act",
            "nsims_planck",
            "no_like_corrections",
            "no_actlike_cmb_corrections",
            "lens_only",
            "trim_lmax",
            "variant",
            "apply_hartlap",
            "limber",
            "nz",
            "kmax",
            "zmax",
            "scale_cov",
            "varying_cmb_alens",
            "act_cmb_rescale",
            "act_calib",
            "stop_at_error",
        ),
    )
    config["likelihood"][PUBLIC_ACT]["version"] = "v1.2"

    # The official covariance path is a NERSC absolute path and affects only
    # proposal efficiency.  Rebuild the same role from the archived official
    # chains so the public config has no private filesystem dependency.
    config["sampler"]["mcmc"]["covmat"] = (
        "{YAML_ROOT}/../runs/prd_extension/wp4_full_cmb/"
        "f0_proposal.covmat"
    )
    config["sampler"]["mcmc"]["seed"] = 4400
    return config


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=OFFICIAL_CONFIG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    config = prepare_config(args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        yaml.safe_dump(config, sort_keys=False, width=100),
        encoding="utf-8",
    )
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
