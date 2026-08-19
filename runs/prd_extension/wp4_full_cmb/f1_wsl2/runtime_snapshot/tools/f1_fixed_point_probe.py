#!/usr/bin/env python3
"""Evaluate the full F1 likelihood at one frozen non-posterior fixed point."""

from __future__ import annotations

import argparse
import json
import os
import platform
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from cobaya.model import get_model
from cobaya.yaml import yaml_load_file


POINT = {
    "logA": 3.036,
    "ns": 0.965,
    "theta_MC_100": 1.04109,
    "ombh2": 0.02237,
    "omch2": 0.1200,
    "tau": 0.0544,
    "w": -1.0,
    "wa": -0.1,
    "Mb": -19.25,
    "A_planck": 1.0,
    "amp_143": 10.0,
    "amp_217": 20.0,
    "amp_143x217": 10.0,
    "n_143": 1.0,
    "n_217": 1.0,
    "n_143x217": 1.0,
    "calTE": 1.0,
    "calEE": 1.0,
}


def _atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        temporary = Path(handle.name)
    os.replace(temporary, path)


def run(config: Path, packages: Path, output: Path) -> dict:
    info = yaml_load_file(str(config))
    info.pop("sampler", None)
    info.pop("output", None)
    info["packages_path"] = str(packages.resolve())
    info["theory"]["camb"]["path"] = "global"
    started = time.monotonic()
    model = get_model(info)
    try:
        posterior = model.logposterior(POINT, make_finite=False)
        likelihood_names = list(model.likelihood)
        prior_names = list(model.prior)
        loglikes = {
            name: float(value)
            for name, value in zip(likelihood_names, posterior.loglikes)
        }
        logpriors = {
            name: float(value)
            for name, value in zip(prior_names, posterior.logpriors)
        }
    finally:
        model.close()
    payload = {
        "schema_version": "wp4-f1-cross-platform-fixed-point-v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "cross-platform full-likelihood drift screen before WSL2 F1",
        "scope_warning": (
            "This fixed non-posterior point is an implementation diagnostic, "
            "not an F1 posterior, best fit, model comparison, or fate result."
        ),
        "environment": {
            "platform": platform.platform(),
            "python": platform.python_version(),
        },
        "fixed_point": POINT,
        "logpost": float(posterior.logpost),
        "logpriors": logpriors,
        "loglikes": loglikes,
        "total_likelihood_chi2": float(-2.0 * sum(loglikes.values())),
        "component_chi2": {
            name: float(-2.0 * value) for name, value in loglikes.items()
        },
        "runtime_seconds": time.monotonic() - started,
    }
    _atomic_json(output, payload)
    print(json.dumps({
        "output": str(output),
        "runtime_seconds": payload["runtime_seconds"],
        "total_likelihood_chi2": payload["total_likelihood_chi2"],
    }, sort_keys=True))
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--packages", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.config, args.packages, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
