import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import numpy as np

from pipeline.append_mocks import AppendSafetyError, append_mocks
from pipeline.make_mocks import build_manifest, write_mock_dir


def digest_tree(root):
    h = hashlib.sha256()
    for p in sorted(Path(root).rglob('*')):
        if p.is_file() and not p.name.endswith('.lock'):
            h.update(str(p.relative_to(root)).encode())
            h.update(p.read_bytes())
    return h.hexdigest()


class AppendMocksTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.out = self.tmp / 'mocks'
        self.out.mkdir()
        self.truth_path = self.tmp / 'truth.json'
        self.truth = {'H0': 70.0, 'ombh2': 0.022, 'omegam': 0.3}
        self.truth_path.write_text(json.dumps(self.truth))
        self.assets = self.fake_assets(self.truth)
        self.seed = 42

    def tearDown(self):
        shutil.rmtree(self.tmp)

    @staticmethod
    def fake_assets(truth):
        class MiniColumn:
            def __init__(self, data):
                self.values = np.array(data, dtype=float)

        class MiniFrame:
            def __init__(self, data):
                self.data = {k: np.array(v, dtype=float) for k, v in data.items()}
            def __getitem__(self, key):
                return MiniColumn(self.data[key])
            def __setitem__(self, key, value):
                self.data[key] = np.array(value, dtype=float)
            def copy(self):
                return MiniFrame({k: v.copy() for k, v in self.data.items()})
            def to_csv(self, path, sep=' ', index=False):
                keys = list(self.data)
                lines = [sep.join(keys)]
                for row in zip(*(self.data[k] for k in keys)):
                    lines.append(sep.join(str(float(x)) for x in row))
                Path(path).write_text('\n'.join(lines) + '\n')

        df = MiniFrame({'m_b_corr': [1.0, 2.0, 3.0], 'aux': [0.0, 1.0, 2.0]})
        return {
            'sn_df': df,
            'sn_mu': np.array([10.0, 20.0, 30.0]),
            'sn_mask': np.array([True, False, True]),
            'L_sn': np.eye(2),
            'bao_rows': [(0.1, 5.0, 'DM_over_rs'), (0.2, 6.0, 'DH_over_rs')],
            'bao_mu': np.array([5.0, 6.0]),
            'L_bao': np.eye(2),
            'cmb_mu': np.array([1.0, 300.0, truth['ombh2']]),
            'L_cmb': np.eye(3),
            'input_fingerprint': {'fixture': 'v1'},
        }

    def assets_factory(self, truth):
        return self.fake_assets(truth)

    def init_existing(self, n=1, seed=42, truth=None, assets=None):
        truth = self.truth if truth is None else truth
        assets = self.assets if assets is None else assets
        rng = np.random.default_rng(seed)
        for k in range(n + 1):
            write_mock_dir(self.out / f'm{k:03d}', k, rng, assets)
        manifest = build_manifest(truth, seed, n, assets['cmb_mu'].tolist(), assets['input_fingerprint'])
        (self.out / 'mocks_manifest.json').write_text(json.dumps(manifest, indent=1))

    def test_dry_run_writes_nothing(self):
        self.init_existing(n=1)
        before = digest_tree(self.out)
        res = append_mocks(self.out, self.truth_path, append=2, dry_run=True, expected_seed=42, assets_factory=self.assets_factory)
        self.assertEqual(res['append_range'], (2, 3))
        self.assertEqual(before, digest_tree(self.out))

    def test_refuses_existing_target_and_preserves_hash(self):
        self.init_existing(n=1)
        (self.out / 'm002').mkdir()
        before = digest_tree(self.out)
        with self.assertRaises(AppendSafetyError):
            append_mocks(self.out, self.truth_path, 1, False, 42, self.assets_factory)
        self.assertEqual(before, digest_tree(self.out))

    def test_rejects_index_gap(self):
        self.init_existing(n=2)
        shutil.rmtree(self.out / 'm001')
        with self.assertRaises(AppendSafetyError):
            append_mocks(self.out, self.truth_path, 1, True, 42, self.assets_factory)

    def test_rejects_manifest_seed_truth_and_fingerprint_mismatch(self):
        self.init_existing(n=1)
        bad = json.loads((self.out / 'mocks_manifest.json').read_text())
        for key, value in [('seed', 7), ('truth', {'H0': 1}), ('input_fingerprint', {'fixture': 'v2'})]:
            good = json.loads((self.out / 'mocks_manifest.json').read_text())
            good[key] = value
            (self.out / 'mocks_manifest.json').write_text(json.dumps(good))
            with self.assertRaises(AppendSafetyError):
                append_mocks(self.out, self.truth_path, 1, True, 42, self.assets_factory)
            (self.out / 'mocks_manifest.json').write_text(json.dumps(bad))

    def test_deterministic_equivalence_to_from_scratch_generation(self):
        self.init_existing(n=1)
        append_mocks(self.out, self.truth_path, 2, False, 42, self.assets_factory)
        appended = [(self.out / f'm{k:03d}' / 'cmb_mean.json').read_text() for k in (2, 3)]
        scratch = self.tmp / 'scratch'; scratch.mkdir()
        rng = np.random.default_rng(42)
        for k in range(4):
            write_mock_dir(scratch / f'm{k:03d}', k, rng, self.assets)
        self.assertEqual(appended, [(scratch / f'm{k:03d}' / 'cmb_mean.json').read_text() for k in (2, 3)])

    def test_simulated_failure_rolls_back_and_manifest_unchanged(self):
        self.init_existing(n=1)
        before = digest_tree(self.out)
        with self.assertRaises(RuntimeError):
            append_mocks(self.out, self.truth_path, 2, False, 42, self.assets_factory, fail_after=1)
        self.assertFalse((self.out / 'm002').exists())
        self.assertEqual(before, digest_tree(self.out))

    def test_lock_and_orphan_staging_fail_closed(self):
        self.init_existing(n=1)
        (self.out / '.append_mocks.lock').mkdir()
        with self.assertRaises(AppendSafetyError):
            append_mocks(self.out, self.truth_path, 1, True, 42, self.assets_factory)
        (self.out / '.append_mocks.lock').rmdir()
        (self.out / '.append-staging-m002').mkdir()
        with self.assertRaises(AppendSafetyError):
            append_mocks(self.out, self.truth_path, 1, True, 42, self.assets_factory)

    def test_manifest_atomic_update_after_dirs(self):
        self.init_existing(n=1)
        append_mocks(self.out, self.truth_path, 1, False, 42, self.assets_factory)
        manifest = json.loads((self.out / 'mocks_manifest.json').read_text())
        self.assertEqual(manifest['previous_n'], 1)
        self.assertEqual(manifest['n'], 2)
        self.assertEqual(manifest['append_range'], [2, 2])
        self.assertTrue((self.out / 'm002').is_dir())


if __name__ == '__main__':
    unittest.main()
