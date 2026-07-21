"""Append-safe Gate-2 mock extension tool.

Usage:
  .venv/bin/python pipeline/append_mocks.py --append K --dry-run
  .venv/bin/python pipeline/append_mocks.py --append K

The tool preserves the legacy seed=42 sequential RNG semantics by replaying the
RNG stream up to the first appended index (O(existing_n) cost). It never
rebuilds m000 and refuses gaps, orphan directories, staging leftovers, manifest
mismatches, incompatible fingerprints, existing targets, or concurrent writers.
"""

import argparse
import json
import os
import shutil
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from pipeline.make_mocks import (GENERATOR_VERSION, advance_rng_to_index,
                                 build_manifest, production_assets,
                                 sha256_obj, write_mock_dir)

DEFAULT_OUT = ROOT / 'runs/gate2/mocks'
DEFAULT_TRUTH = ROOT / 'runs/gate2/truth_lcdm_d0.json'


class AppendSafetyError(RuntimeError):
    pass


@contextmanager
def exclusive_lock(lock_dir):
    try:
        os.mkdir(lock_dir)
    except FileExistsError as e:
        raise AppendSafetyError(f"concurrent append lock exists: {lock_dir}") from e
    try:
        yield
    finally:
        try:
            os.rmdir(lock_dir)
        except FileNotFoundError:
            pass


def load_manifest(out_dir):
    path = out_dir / 'mocks_manifest.json'
    if not path.exists():
        raise AppendSafetyError(f"missing manifest: {path}")
    return json.loads(path.read_text())


def manifest_n(manifest):
    try:
        n = int(manifest['n'])
        seed = int(manifest['seed'])
        truth = manifest['truth']
    except Exception as e:
        raise AppendSafetyError("manifest missing required n/seed/truth fields") from e
    if n < 0:
        raise AppendSafetyError("manifest n must be non-negative")
    return n, seed, truth


def mock_indices(out_dir):
    indices = []
    staging = []
    for p in out_dir.iterdir():
        if p.is_dir() and p.name.startswith('m') and p.name[1:].isdigit():
            indices.append(int(p.name[1:]))
        if p.name.startswith('.append-staging-') or p.name.endswith('.tmp'):
            staging.append(p.name)
    return sorted(indices), staging


def validate_existing(out_dir, manifest, expected_truth, expected_seed=None, expected_input_fingerprint=None):
    n, seed, truth = manifest_n(manifest)
    if expected_seed is not None and seed != expected_seed:
        raise AppendSafetyError(f"manifest seed {seed} != expected seed {expected_seed}")
    if truth != expected_truth or manifest.get('truth_fingerprint') not in (None, sha256_obj(expected_truth)):
        raise AppendSafetyError("manifest truth does not match requested truth")
    if expected_input_fingerprint is not None and manifest.get('input_fingerprint') not in (None, expected_input_fingerprint):
        raise AppendSafetyError("manifest input fingerprint is incompatible")
    indices, staging = mock_indices(out_dir)
    if staging:
        raise AppendSafetyError(f"orphan staging/temp entries present: {staging}")
    expected = list(range(n + 1))
    if indices != expected:
        raise AppendSafetyError(f"mock index set is not contiguous 0..{n}: {indices}")
    return n, seed


def atomic_write_json(path, payload):
    fd, tmp = tempfile.mkstemp(prefix=path.name + '.', suffix='.tmp', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(payload, f, indent=1)
            f.write('\n')
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def append_mocks(out_dir=DEFAULT_OUT, truth_path=DEFAULT_TRUTH, append=0, dry_run=False,
                 expected_seed=None, assets_factory=production_assets, fail_after=None):
    out_dir = Path(out_dir)
    truth = json.loads(Path(truth_path).read_text()) if truth_path else None
    if append <= 0:
        raise AppendSafetyError("--append must be a positive integer")
    with exclusive_lock(out_dir / '.append_mocks.lock'):
        manifest = load_manifest(out_dir)
        assets = assets_factory(truth)
        n_old, seed = validate_existing(out_dir, manifest, truth, expected_seed, assets.get('input_fingerprint'))
        start, end = n_old + 1, n_old + append
        for k in range(start, end + 1):
            if (out_dir / f'm{k:03d}').exists():
                raise AppendSafetyError(f"target already exists: m{k:03d}")
        new_manifest = build_manifest(truth, seed, end, assets['cmb_mu'].tolist(),
                                      assets.get('input_fingerprint'), n_old, (start, end))
        if dry_run:
            return {'old_n': n_old, 'new_n': end, 'append_range': (start, end), 'dry_run': True}
        rng = np.random.default_rng(seed)
        advance_rng_to_index(rng, start, assets)
        made = []
        try:
            for k in range(start, end + 1):
                staging = out_dir / f'.append-staging-m{k:03d}'
                final = out_dir / f'm{k:03d}'
                if staging.exists() or final.exists():
                    raise AppendSafetyError(f"refusing to overwrite {staging if staging.exists() else final}")
                write_mock_dir(staging, k, rng, assets)
                os.replace(staging, final)
                made.append(final)
                if fail_after is not None and len(made) >= fail_after:
                    raise RuntimeError("simulated append failure")
            atomic_write_json(out_dir / 'mocks_manifest.json', new_manifest)
        except Exception:
            for p in made:
                if p.exists():
                    shutil.rmtree(p)
            raise
        return {'old_n': n_old, 'new_n': end, 'append_range': (start, end), 'dry_run': False}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--append', type=int, required=True, help='number of mocks to append')
    ap.add_argument('--dry-run', action='store_true', help='validate and report without writing')
    ap.add_argument('--out-dir', default=str(DEFAULT_OUT))
    ap.add_argument('--truth', default=str(DEFAULT_TRUTH))
    ap.add_argument('--seed', type=int, default=42, help='expected manifest seed (default: 42)')
    args = ap.parse_args(argv)
    try:
        res = append_mocks(args.out_dir, args.truth, args.append, args.dry_run, args.seed)
    except AppendSafetyError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    print(json.dumps(res, sort_keys=True))
    if not args.dry_run:
        print("RNG replay note: preserved legacy sequential seed semantics by replaying prior draws; cost is O(existing mock count).")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
