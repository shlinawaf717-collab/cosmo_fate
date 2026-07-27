#!/usr/bin/env python3
"""Build a deterministic, file-level hash inventory for WP4 F0 inputs."""

from __future__ import annotations

import argparse
import hashlib
import json
from importlib import metadata
from pathlib import Path

from pipeline.wp4_preflight import (
    PACKAGES_ROOT,
    ROOT,
    WP4_ROOT,
    display_path,
    sha256_file,
)


DEFAULT_OUTPUT = WP4_ROOT / "input_manifest.json"

INPUT_GROUPS = {
    "desi_dr2_bao": [
        PACKAGES_ROOT
        / "data/bao_data/desi_bao_dr2/desi_gaussian_bao_ALL_GCcomb_mean.txt",
        PACKAGES_ROOT
        / "data/bao_data/desi_bao_dr2/desi_gaussian_bao_ALL_GCcomb_cov.txt",
    ],
    "pantheonplus": [
        PACKAGES_ROOT / "data/sn_data/PantheonPlus/config.dataset",
        PACKAGES_ROOT / "data/sn_data/PantheonPlus/Pantheon+SH0ES.dat",
        PACKAGES_ROOT
        / "data/sn_data/PantheonPlus/Pantheon+SH0ES_STAT+SYS.cov",
    ],
    "planck_2018_pr3_lowl": [
        PACKAGES_ROOT / "data/planck_2018",
    ],
    "planck_supplementary": [
        PACKAGES_ROOT / "data/planck_supp_data_and_covmats",
    ],
    "planck_npipe_camspec": [
        PACKAGES_ROOT / "data/planck_NPIPE_CamSpec",
    ],
    "act_dr6_lensing_v1p2": [
        PACKAGES_ROOT / "data/ACT_dr6_likelihood/v1.2",
    ],
}

SOURCES = {
    "desi_dr2_bao": {
        "version": "CobayaSampler/bao_data v2.6",
        "url": "https://github.com/CobayaSampler/bao_data",
    },
    "pantheonplus": {
        "version": "CobayaSampler/sn_data v1.8",
        "url": "https://github.com/CobayaSampler/sn_data",
    },
    "planck_2018_pr3_lowl": {
        "version": "Planck baseline R3.00, PLA product 151902",
        "url": (
            "https://pla.esac.esa.int/pla-sl/data-action?"
            "COSMOLOGY.COSMOLOGY_OID=151902"
        ),
    },
    "planck_supplementary": {
        "version": "CobayaSampler/planck_supp_data_and_covmats v2.1",
        "url": (
            "https://github.com/CobayaSampler/"
            "planck_supp_data_and_covmats/releases/tag/v2.1"
        ),
    },
    "planck_npipe_camspec": {
        "version": "CobayaSampler/planck_native_data v1, CamSpec_NPIPE.zip",
        "url": (
            "https://github.com/CobayaSampler/"
            "planck_native_data/releases/tag/v1"
        ),
    },
    "act_dr6_lensing_v1p2": {
        "version": "ACT DR6 likelihood data v1.2",
        "url": (
            "https://lambda.gsfc.nasa.gov/data/suborbital/ACT/ACT_dr6/"
            "likelihood/data/ACT_dr6_likelihood_v1.2.tgz"
        ),
    },
}

SOFTWARE_DISTRIBUTIONS = (
    "cobaya",
    "camb",
    "clipy-like",
    "act-dr6-lenslike",
    "numpy",
    "scipy",
)


class WP4InputManifestError(RuntimeError):
    """Raised when a registered input root is absent or malformed."""


def _files_for_paths(paths: list[Path]) -> list[Path]:
    files = []
    for path in paths:
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files.extend(item for item in path.rglob("*") if item.is_file())
        else:
            raise WP4InputManifestError(f"missing WP4 input: {path}")
    return sorted(set(files), key=display_path)


def _tree_digest(records: list[dict]) -> str:
    digest = hashlib.sha256()
    for record in records:
        digest.update(record["path"].encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(record["bytes"]).encode("ascii"))
        digest.update(b"\0")
        digest.update(record["sha256"].encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def build_manifest(groups: dict[str, list[Path]] | None = None) -> dict:
    selected = INPUT_GROUPS if groups is None else groups
    result_groups = {}
    all_records = []
    for name, paths in selected.items():
        files = _files_for_paths(paths)
        records = [
            {
                "path": display_path(path),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for path in files
        ]
        all_records.extend(records)
        result_groups[name] = {
            "source": SOURCES.get(name),
            "files": records,
            "file_count": len(records),
            "total_bytes": sum(record["bytes"] for record in records),
            "tree_sha256": _tree_digest(records),
        }

    unique_records = {
        record["path"]: record for record in all_records
    }
    ordered_records = [
        unique_records[path] for path in sorted(unique_records)
    ]
    versions = {}
    for distribution in SOFTWARE_DISTRIBUTIONS:
        try:
            versions[distribution] = metadata.version(distribution)
        except metadata.PackageNotFoundError:
            versions[distribution] = None

    return {
        "schema_version": "wp4-input-manifest-v1",
        "scope": (
            "Complete local payloads registered for the WP4 F0 full-CMB "
            "reproduction; no inference or fate calculation is represented."
        ),
        "software": versions,
        "groups": result_groups,
        "totals": {
            "unique_file_count": len(ordered_records),
            "total_bytes": sum(record["bytes"] for record in ordered_records),
            "tree_sha256": _tree_digest(ordered_records),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    manifest = build_manifest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        f"wrote {args.output}: {manifest['totals']['unique_file_count']} files, "
        f"{manifest['totals']['total_bytes']} bytes, "
        f"tree={manifest['totals']['tree_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
