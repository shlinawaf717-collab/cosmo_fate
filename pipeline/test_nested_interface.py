import json
import os
import sys
from types import SimpleNamespace

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline import nested_core as nc


def fake_results():
    return SimpleNamespace(
        samples=np.array([[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]),
        logwt=np.array([-1000.0, -1001.0, -np.inf]),
        logz=np.array([-999.6867383]),
        logzerr=np.array([0.12]),
        ncall=np.array([2, 3, 5]),
    )


def test_stable_weights_ignore_nonfinite_and_normalize():
    weights, ess = nc.stable_normalized_weights([-1000.0, -1001.0, -np.inf, np.nan], -999.0)
    assert np.isclose(weights.sum(), 1.0)
    assert weights[2] == 0.0
    assert weights[3] == 0.0
    assert weights[0] > weights[1]
    assert 1.0 < ess < 2.1


def test_resampling_is_seeded_and_deterministic():
    res1, idx1, w1, ess1 = nc.resample_equal_weight(fake_results().samples, fake_results().logwt,
                                                     fake_results().logz[-1], seed=7, max_samples=5)
    res2, idx2, w2, ess2 = nc.resample_equal_weight(fake_results().samples, fake_results().logwt,
                                                     fake_results().logz[-1], seed=7, max_samples=5)
    np.testing.assert_array_equal(idx1, idx2)
    np.testing.assert_array_equal(res1, res2)
    np.testing.assert_allclose(w1, w2)
    assert ess1 == ess2
    assert len(res1) == 2  # capped at positive-weight support, preserving legacy behavior


def test_schema_and_legacy_keys_are_both_present():
    cfg = nc.NestedRunConfig(kind='cpl', names=['w', 'wa'], bounds=[(-3.0, 1.0), (-3.0, 2.0)],
                             evidence_correction=0.25, seed=11)
    out = nc.summarize_results(fake_results(), cfg)
    samp, _, weights, ess = nc.resample_equal_weight(fake_results().samples, fake_results().logwt,
                                                     fake_results().logz[-1], seed=11, max_samples=10)
    nc.add_resampling_audit(out, weights=weights, ess=ess, n_equal_weight=len(samp))
    probs = {'CRUNCH': 0.0, 'RIP': 0.5, 'DS': 0.5, 'DECAY': 0.0, 'OTHER': 0.0}
    nc.add_fate_summary(out, probs, 2)
    out['lnZ_CPL'] = out['logZ']
    out['lnZ_CPL_err'] = out['logZerr']
    assert out['schema_version'] == nc.SCHEMA_VERSION
    assert out['seed'] == 11
    assert out['resampling_method'] == nc.RESAMPLING_METHOD
    assert out['n_samples'] == 2
    assert 'ess' in out and 'ncall' in out and 'P_fate_nested' in out
    assert 'lnZ_CPL' in out and 'lnZ_CPL_err' in out
    assert 'fixed-seed equal-weight resample only' in out['uncertainty_note']


def test_atomic_write_json_creates_parent_and_replaces(tmp_path):
    path = tmp_path / 'nested' / 'out.json'
    nc.atomic_write_json(str(path), {'a': 1})
    assert json.loads(path.read_text()) == {'a': 1}
    nc.atomic_write_json(str(path), {'b': 2})
    assert json.loads(path.read_text()) == {'b': 2}
    assert not list(path.parent.glob('*.tmp'))


def test_prior_transform_and_bad_inputs_fail():
    np.testing.assert_allclose(nc.prior_transform([0.0, 1.0], [(2.0, 4.0), (10.0, 20.0)]), [2.0, 20.0])
    with pytest.raises(ValueError, match=r'\[0, 1\]'):
        nc.prior_transform([1.2], [(0.0, 1.0)])
    with pytest.raises(ValueError, match='non-finite'):
        nc.stable_normalized_weights([np.nan, -np.inf])
    with pytest.raises(ValueError, match='unknown nested kind'):
        nc.NestedRunConfig(kind='bad', names=['x'], bounds=[(0.0, 1.0)]).validate()
    with pytest.raises(ValueError, match='unknown fate label'):
        nc.classify_samples(np.array([[1.0]]), ['x'], lambda params: 'BOGUS')


def test_verify_cli_signature_kept():
    import pipeline.nested_verify as nv
    assert nv.main.__defaults__[:3] == (500, 3, None)


def test_run_dynesty_receives_recorded_seed(monkeypatch):
    calls = {}

    class FakePool:
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeContext:
        def Pool(self, nproc, initializer=None, initargs=()):
            calls['pool'] = (nproc, initializer, initargs)
            return FakePool()

    class FakeSampler:
        def __init__(self, loglike, ptform, ndim, **kwargs):
            calls['ndim'] = ndim
            calls['kwargs'] = kwargs
            self.results = SimpleNamespace(ok=True)
        def run_nested(self, **kwargs):
            calls['run_nested'] = kwargs

    monkeypatch.setitem(sys.modules, 'dynesty', SimpleNamespace(NestedSampler=FakeSampler))
    import multiprocessing
    monkeypatch.setattr(multiprocessing, 'get_context', lambda method: FakeContext())
    cfg = nc.NestedRunConfig(kind='cpl', names=['w'], bounds=[(-3.0, 1.0)],
                             nlive=10, nproc=2, seed=123, dlogz=0.2, maxiter=7)
    result = nc.run_dynesty(cfg, lambda x: -float(x[0] ** 2))
    assert result.ok
    assert calls['ndim'] == 1
    assert calls['kwargs']['nlive'] == 10
    seeded_draw = calls['kwargs']['rstate'].integers(0, 2**31)
    expected_draw = np.random.default_rng(123).integers(0, 2**31)
    assert seeded_draw == expected_draw
    assert calls['run_nested'] == {'dlogz': 0.2, 'print_progress': False, 'maxiter': 7}
