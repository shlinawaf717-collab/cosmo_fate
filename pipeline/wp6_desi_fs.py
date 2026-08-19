"""Pinned public DESI DR1 full-shape components exposed to Cobaya.

This module is deliberately a thin registration layer.  The scientific
implementation remains the archived, hash-checked DESI release code under
``data/wp6_desi_dr1/code/official_likelihood``.
"""

import sys
from pathlib import Path

from cobaya.yaml import yaml_load_file


ROOT = Path(__file__).resolve().parents[1]
OFFICIAL_CODE = (
    ROOT / "data/wp6_desi_dr1/code/official_likelihood/dr1/cobaya"
)
if str(OFFICIAL_CODE) not in sys.path:
    sys.path.insert(0, str(OFFICIAL_CODE))

from desi_fs_bao_all import desi_fs_bao_all as _OfficialDESIFSBAO  # noqa: E402
from reptvelocileptors import reptvelocileptors as _OfficialReptVelocileptors  # noqa: E402


class DESIDR1FSBAO(_OfficialDESIFSBAO):
    """Cobaya-visible wrapper for the pinned official DR1 likelihood."""

    type = "FS_BAO"
    params = yaml_load_file(str(OFFICIAL_CODE / "desi_fs_bao_all.yaml"))["params"]
    data_dir: str
    observable_name: str = "spectrum-poles-rotated+bao-recon"
    tracers: list
    solve: str = "marg"


class DESIDR1ReptVelocileptors(_OfficialReptVelocileptors):
    """Cobaya-visible wrapper for the pinned official DR1 theory module."""

    is_physical_prior: bool = True
    stop_at_error: bool = True
